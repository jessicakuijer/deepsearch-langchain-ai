"""Persistance locale des recherches et préférences."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SANDBOX_DIR = Path(__file__).resolve().parent.parent / "sandbox"
HISTORY_PATH = SANDBOX_DIR / "history.json"
PREFERENCES_PATH = SANDBOX_DIR / "preferences.json"

DEFAULT_PREFERENCES = {
    "auto_pdf": True,
    "notify": True,
    "lang": "fr",
}


def _ensure_sandbox() -> None:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_sandbox()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_sandbox()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_preferences() -> dict:
    prefs = _read_json(PREFERENCES_PATH, DEFAULT_PREFERENCES.copy())
    merged = DEFAULT_PREFERENCES.copy()
    merged.update({k: v for k, v in prefs.items() if k in DEFAULT_PREFERENCES})
    return merged


def save_preferences(prefs: dict) -> None:
    merged = DEFAULT_PREFERENCES.copy()
    merged.update({k: v for k, v in prefs.items() if k in DEFAULT_PREFERENCES})
    _write_json(PREFERENCES_PATH, merged)


def load_history() -> list[dict]:
    data = _read_json(HISTORY_PATH, [])
    return data if isinstance(data, list) else []


def save_history(entries: list[dict]) -> None:
    _write_json(HISTORY_PATH, entries)


def add_history_entry(
    query: str,
    criteria: str,
    *,
    status: str,
    duration_s: int,
    sources_count: int,
    report_content: str,
    attempt_count: int = 1,
    sources: list[dict] | None = None,
) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "query": query,
        "criteria": criteria,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": duration_s,
        "status": status,
        "sources_count": sources_count,
        "attempt_count": attempt_count,
        "report_preview": (report_content or "")[:200],
        "report_content": report_content or "",
        "sources": sources or [],
    }
    entries = load_history()
    entries.insert(0, entry)
    save_history(entries[:100])
    return entry


def get_history_entry(entry_id: str) -> dict | None:
    for entry in load_history():
        if entry.get("id") == entry_id:
            return entry
    return None


def get_recent_history(limit: int = 3) -> list[dict]:
    return load_history()[:limit]


def format_relative_time(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        minutes = int(delta.total_seconds() // 60)
        if minutes < 60:
            return f"Il y a {max(1, minutes)} min" if minutes > 0 else "À l'instant"
        hours = minutes // 60
        if hours < 24:
            return f"Il y a {hours} h"
        days = hours // 24
        if days < 7:
            return f"Il y a {days} j"
        return dt.strftime("%d %b")
    except (ValueError, TypeError):
        return iso_date[:10] if iso_date else ""


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} s"
    minutes = seconds // 60
    remainder = seconds % 60
    if remainder:
        return f"{minutes} min {remainder} s"
    return f"{minutes} min"
