"""Services métier DeepSearch (PDF, Pushover, Sidekick)."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from sidekick import Sidekick

load_dotenv()

PUSHOVER_MESSAGE_LIMIT = 1024
PUSHOVER_TITLE_LIMIT = 250
SANDBOX_REPORTS_DIR = Path(__file__).resolve().parent.parent / "sandbox" / "reports"
PUSHOVER_PART_TAG_RESERVE = 8  # ex. "[12/99]\n"


def _strip_markdown_for_push(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and all(set(cell) <= set("-: ") for cell in cells):
                continue
            lines.append(" · ".join(cell for cell in cells if cell))
        else:
            lines.append(line.rstrip())
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _build_pushover_messages(
    query: str,
    report_content: str,
    *,
    duration_s: int = 0,
    sources_count: int = 0,
    txt_filename: str | None = None,
) -> list[tuple[str, str]]:
    plain = _strip_markdown_for_push(report_content or "Aucun contenu disponible.")
    header_lines = [f"Recherche : {query.strip()}"]
    meta_bits = []
    if duration_s:
        meta_bits.append(f"{duration_s} s")
    if sources_count:
        meta_bits.append(f"{sources_count} source(s)")
    if meta_bits:
        header_lines.append(" · ".join(meta_bits))
    if txt_filename:
        header_lines.append(f"TXT : sandbox/reports/{txt_filename}")
    header = "\n".join(header_lines)
    separator = "\n\n---\n\n"

    first_overhead = len(header) + len(separator) + PUSHOVER_PART_TAG_RESERVE
    other_overhead = PUSHOVER_PART_TAG_RESERVE
    first_limit = max(80, PUSHOVER_MESSAGE_LIMIT - first_overhead)
    other_limit = max(80, PUSHOVER_MESSAGE_LIMIT - other_overhead)

    body_chunks: list[str] = []
    remaining = plain
    while remaining:
        limit = first_limit if not body_chunks else other_limit
        if len(remaining) <= limit:
            body_chunks.append(remaining)
            break
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut < limit // 2:
            cut = limit
        body_chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    total = len(body_chunks)
    messages: list[tuple[str, str]] = []
    for index, chunk in enumerate(body_chunks, start=1):
        tag = f"[{index}/{total}]\n" if total > 1 else ""
        if index == 1:
            message = f"{header}{separator}{tag}{chunk}"
        else:
            message = f"{tag}{chunk}"
        messages.append(("Rapport DeepSearch", message[:PUSHOVER_MESSAGE_LIMIT]))
    return messages


def _config_value(key: str) -> str | None:
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return None


class DeepSearchApp:
    def __init__(self):
        self.sidekick = None
        self.pushover_token = _config_value("PUSHOVER_TOKEN")
        self.pushover_user = _config_value("PUSHOVER_USER")
        self.pushover_url = "https://api.pushover.net/1/messages.json"

    async def initialize_sidekick(self):
        if self.sidekick is not None and self.sidekick.graph is not None:
            return self.sidekick

        if self.sidekick is not None:
            try:
                self.sidekick.cleanup()
            except Exception:
                pass
            self.sidekick = None

        sidekick = Sidekick()
        await sidekick.setup()
        if sidekick.graph is None:
            raise RuntimeError("Impossible d'initialiser l'agent DeepSearch (graphe LangGraph absent).")
        self.sidekick = sidekick
        return self.sidekick

    def generate_pdf_report(
        self,
        query: str,
        report_content: str,
        *,
        duration_s: int = 0,
        sources_count: int = 0,
        attempt_count: int = 1,
    ) -> tuple[bytes, str]:
        from services.pdf_report import build_pdf_report

        pdf_bytes = build_pdf_report(
            query,
            report_content,
            duration_s=duration_s,
            sources_count=sources_count,
            attempt_count=attempt_count,
        )
        filename = f"rapport_deepsearch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf_bytes, filename

    def generate_pdf_from_messages(self, query: str, results: list) -> tuple[bytes, str]:
        parts = []
        for result in results:
            if isinstance(result, dict) and result.get("content"):
                content = result["content"]
                if "Evaluator Feedback" not in content:
                    parts.append(content)
        report_content = "\n\n".join(parts) if parts else str(results)
        return self.generate_pdf_report(query, report_content)

    def save_report_txt(
        self,
        query: str,
        report_content: str,
        *,
        duration_s: int = 0,
        sources_count: int = 0,
    ) -> tuple[Path | None, str | None]:
        filename = f"rapport_deepsearch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        header_lines = [
            "RAPPORT DE RECHERCHE — DeepSearch",
            f"Requête : {query.strip()}",
            f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ]
        if duration_s or sources_count:
            header_lines.append(f"Durée : {duration_s} s · Sources : {sources_count}")
        header_lines.extend(["", "---", ""])
        try:
            SANDBOX_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            path = SANDBOX_REPORTS_DIR / filename
            path.write_text(
                "\n".join(header_lines) + (report_content or "Aucun contenu disponible."),
                encoding="utf-8",
            )
            return path, filename
        except OSError:
            return None, None

    def _send_pushover_message(self, title: str, message: str) -> tuple[bool, str]:
        if not self.pushover_token or not self.pushover_user:
            return False, "Tokens Pushover non configurés"

        data = {
            "token": self.pushover_token,
            "user": self.pushover_user,
            "message": message[:PUSHOVER_MESSAGE_LIMIT],
            "title": title[:PUSHOVER_TITLE_LIMIT],
        }
        try:
            response = requests.post(self.pushover_url, data=data, timeout=30)
            if response.status_code == 200:
                return True, ""
            try:
                detail = response.json().get("errors", [response.text])
                return False, f"Erreur Pushover ({response.status_code}): {detail}"
            except Exception:
                return False, f"Erreur Pushover: {response.status_code}"
        except Exception as e:
            return False, f"Erreur lors de l'envoi: {str(e)}"

    def send_pushover_notification(self, message: str) -> tuple[bool, str]:
        ok, err = self._send_pushover_message("Rapport DeepSearch", message)
        if ok:
            return True, "Notification envoyée avec succès"
        return False, err

    def send_pushover_report(
        self,
        query: str,
        report_content: str,
        *,
        duration_s: int = 0,
        sources_count: int = 0,
    ) -> tuple[bool, str]:
        if not self.pushover_token or not self.pushover_user:
            return False, "Tokens Pushover non configurés"

        _, txt_filename = self.save_report_txt(
            query,
            report_content,
            duration_s=duration_s,
            sources_count=sources_count,
        )
        messages = _build_pushover_messages(
            query,
            report_content,
            duration_s=duration_s,
            sources_count=sources_count,
            txt_filename=txt_filename,
        )
        sent = 0
        for title, body in messages:
            ok, err = self._send_pushover_message(title, body)
            if not ok:
                if sent:
                    return False, f"Échec après {sent} notification(s) : {err}"
                return False, err
            sent += 1

        if sent == 1:
            suffix = f" · TXT : sandbox/reports/{txt_filename}" if txt_filename else ""
            return True, f"Notification envoyée{suffix}"
        suffix = f" · TXT : sandbox/reports/{txt_filename}" if txt_filename else ""
        return True, f"{sent} notifications envoyées (rapport découpé){suffix}"

    async def process_search(self, query, success_criteria):
        sidekick = await self.initialize_sidekick()
        return await sidekick.run_superstep(query, success_criteria, [])
