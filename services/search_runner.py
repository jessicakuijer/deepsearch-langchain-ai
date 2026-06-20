"""Orchestration recherche avec streaming d'événements."""

from __future__ import annotations

import re
import time
from typing import Callable
from urllib.parse import urlparse

from ui.history_store import add_history_entry, format_duration

STEP_TEMPLATES = {
    "plan": {"tool": "Planification", "title": "Analyse de la requête", "detail": "Décomposition de la tâche et des critères de succès."},
    "search": {"tool": "Recherche web", "title": "Recherche Google (Serper)", "detail": "Collecte des résultats pertinents."},
    "browser": {"tool": "Navigateur", "title": "Navigation web", "detail": "Extraction du contenu des pages."},
    "wiki": {"tool": "Wikipédia", "title": "Consultation Wikipédia", "detail": "Récupération du contexte encyclopédique."},
    "python": {"tool": "Python", "title": "Analyse des données", "detail": "Exécution de code pour agréger ou calculer."},
    "write": {"tool": "Rédaction", "title": "Rédaction du rapport", "detail": "Structuration de la réponse finale."},
    "eval": {"tool": "Évaluation", "title": "Vérification des critères", "detail": "Contrôle qualité par l'évaluateur."},
    "done": {"tool": "Finalisation", "title": "Finalisation", "detail": "Préparation du rapport et des actions."},
}


def cred_for_domain(domain: str) -> tuple[str, str]:
    d = (domain or "").lower()
    if "wikipedia" in d or ".gov" in d or ".gouv." in d:
        return "Fiabilité moyenne", "#B8893B"
    return "Fiabilité élevée", "#1F8A5B"


def extract_domain(text: str) -> str:
    urls = re.findall(r"https?://[^\s\)\]\"']+", text or "")
    if urls:
        try:
            return urlparse(urls[0]).netloc.replace("www.", "")
        except Exception:
            pass
    return "source web"


def extract_sources_from_output(output: str, title: str | None = None) -> list[dict]:
    domain = extract_domain(output)
    cred, cred_color = cred_for_domain(domain)
    return [{"t": title or domain, "d": domain, "cred": cred, "cred_color": cred_color}]


def make_step(kind: str, *, detail: str | None = None, status: str = "pending") -> dict:
    tpl = STEP_TEMPLATES.get(kind, STEP_TEMPLATES["plan"])
    return {
        "kind": kind,
        "tool": tpl["tool"],
        "title": tpl["title"],
        "detail": detail or tpl["detail"],
        "status": status,
    }


def build_initial_steps(playwright_available: bool = True) -> list[dict]:
    kinds = ["plan", "search"]
    if playwright_available:
        kinds.append("browser")
    kinds.extend(["wiki", "python", "write", "eval", "done"])
    return [make_step(k, status="pending" if i else "active") for i, k in enumerate(kinds)]


def activate_step(steps: list[dict], kind: str, detail: str | None = None) -> list[dict]:
    updated = []
    found = False
    for step in steps:
        s = dict(step)
        if s["kind"] == kind and not found:
            s["status"] = "active"
            if detail:
                s["detail"] = detail
            found = True
        elif s["status"] == "active" and s["kind"] != kind:
            s["status"] = "done"
        updated.append(s)
    if not found:
        updated.append(make_step(kind, detail=detail, status="active"))
    return updated


def complete_step(steps: list[dict], kind: str) -> list[dict]:
    updated = []
    for step in steps:
        s = dict(step)
        if s["kind"] == kind:
            s["status"] = "done"
        updated.append(s)
    return updated


def progress_pct(steps: list[dict]) -> int:
    if not steps:
        return 0
    done = sum(1 for s in steps if s.get("status") == "done")
    return round(done / len(steps) * 100)


def fmt_elapsed(ms: int) -> str:
    s = max(0, ms // 1000)
    m = s // 60
    r = s % 60
    return f"{m}:{r:02d}"


def extract_report_from_messages(messages: list) -> tuple[str, str, int]:
    report = ""
    feedback = ""
    attempts = 0
    for msg in messages:
        content = ""
        if isinstance(msg, dict):
            content = msg.get("content") or ""
        elif hasattr(msg, "content"):
            content = msg.content or ""
        if "Evaluator Feedback" in content:
            feedback = content
        elif content and not content.startswith("Erreur"):
            if not report or len(content) > len(report):
                report = content
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            if "attempt" in str(msg.get("content", "")).lower():
                attempts += 1
    return report, feedback, max(1, attempts)


class SearchSession:
    def __init__(self, *, playwright_available: bool = True):
        self.playwright_available = playwright_available
        self.steps = build_initial_steps(playwright_available)
        self.sources: list[dict] = []
        self.start_time = time.time()
        self.report_content = ""
        self.evaluator_feedback = ""
        self.attempt_count = 1
        self.messages: list = []
        self._seen_tools: set[str] = set()

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    def on_event(self, event: dict) -> None:
        kind = event.get("kind")
        detail = event.get("detail")
        if kind:
            self.steps = activate_step(self.steps, kind, detail)
        if event.get("complete_kind"):
            self.steps = complete_step(self.steps, event["complete_kind"])
        for src in event.get("sources", []):
            domain = src.get("d") or src.get("domain")
            if not any((existing.get("d") or existing.get("domain")) == domain for existing in self.sources):
                self.sources.append(src)

    async def run(self, app, query: str, criteria: str, on_update: Callable | None = None) -> dict:
        def emit(event: dict):
            self.on_event(event)
            if on_update:
                on_update(self)

        emit({"kind": "plan", "detail": f"Requête : {query[:120]}"})

        try:
            sidekick = await app.initialize_sidekick()
            result = await sidekick.run_superstep_streaming(
                query,
                criteria or "La réponse doit être claire, précise et complète",
                on_event=lambda ev: self._handle_stream_event(ev, emit),
            )
            self.messages = result.get("messages", [])
            self.report_content = result.get("report_content", "")
            self.evaluator_feedback = result.get("evaluator_feedback", "")
            self.attempt_count = result.get("attempt_count", 1)
        except Exception as e:
            self.report_content = f"Erreur lors de la recherche : {e}"
            if "Graph LangGraph" in str(e) or "initialiser l'agent" in str(e):
                app.sidekick = None
            emit({"complete_kind": "plan"})
            emit({"complete_kind": "done", "detail": str(e)[:160]})

        for kind in [s["kind"] for s in self.steps]:
            self.steps = complete_step(self.steps, kind)
        if on_update:
            on_update(self)

        duration_s = max(1, self.elapsed_ms() // 1000)
        status = "done" if self.report_content and "Erreur" not in self.report_content[:40] else "failed"
        entry = add_history_entry(
            query,
            criteria,
            status=status,
            duration_s=duration_s,
            sources_count=len(self.sources),
            report_content=self.report_content,
            attempt_count=self.attempt_count,
            sources=self.sources,
        )
        return {
            "report_content": self.report_content,
            "evaluator_feedback": self.evaluator_feedback,
            "attempt_count": self.attempt_count,
            "duration_s": duration_s,
            "sources": self.sources,
            "steps": self.steps,
            "history_id": entry["id"],
            "status": status,
            "duration_label": format_duration(duration_s),
        }

    def _handle_stream_event(self, ev: dict, emit: Callable) -> None:
        event_type = ev.get("event")
        name = (ev.get("name") or "").lower()
        data = ev.get("data") or {}

        if event_type == "on_chain_start" and name == "worker":
            emit(
                {
                    "complete_kind": "plan",
                    "kind": "search",
                    "detail": "Agent worker — analyse de la requête et choix des outils…",
                }
            )

        elif event_type == "on_tool_start":
            tool_name = name
            if tool_name in self._seen_tools and tool_name not in ("search",):
                return
            self._seen_tools.add(tool_name)

            if "search" in tool_name or tool_name == "search":
                emit({"kind": "search", "detail": "Interrogation de l'API Serper…"})
            elif any(x in tool_name for x in ("navigate", "click", "browser", "extract", "current")):
                if self.playwright_available:
                    emit({"kind": "browser", "detail": f"Outil navigateur : {tool_name}"})
            elif "wikipedia" in tool_name or "wiki" in tool_name:
                emit({"kind": "wiki", "detail": "Consultation de Wikipédia…"})
            elif "python" in tool_name or "repl" in tool_name:
                emit({"kind": "python", "detail": "Exécution de code Python…"})
            elif any(x in tool_name for x in ("write", "file", "copy", "move", "list")):
                emit({"kind": "write", "detail": f"Fichier : {tool_name}"})
            elif "push" in tool_name:
                emit({"kind": "done", "detail": "Envoi de notification Pushover…"})

        elif event_type == "on_tool_end":
            output = str(data.get("output") or data.get("result") or "")
            tool_name = name
            sources = extract_sources_from_output(output)
            if sources:
                emit({"sources": sources})
            if "search" in tool_name:
                emit({"complete_kind": "search", "kind": "browser" if self.playwright_available else "wiki"})
            elif "wikipedia" in tool_name:
                emit({"complete_kind": "wiki", "kind": "python"})
            elif "python" in tool_name or "repl" in tool_name:
                emit({"complete_kind": "python", "kind": "write"})

        elif event_type == "on_chain_start" and "evaluator" in name:
            emit({"kind": "eval", "detail": "Vérification des critères de succès…"})

        elif event_type == "on_chain_end" and "evaluator" in name:
            emit({"complete_kind": "eval", "kind": "done", "detail": "Critères évalués."})

        elif event_type == "on_chain_end" and name == "langgraph":
            emit({"complete_kind": "done", "detail": "Recherche terminée."})
