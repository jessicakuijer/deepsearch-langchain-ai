"""État de session Streamlit partagé."""

from __future__ import annotations

import streamlit as st

from ui.history_store import load_preferences

VIEWS = ("home", "live", "report", "history", "settings")


def init_session_state(*, playwright_available: bool = True) -> None:
    defaults = {
        "view": "home",
        "query": "",
        "criteria": "",
        "live_steps": [],
        "sources": [],
        "running": False,
        "done": False,
        "elapsed_ms": 0,
        "search_started": False,
        "current_run_id": None,
        "report_content": "",
        "report_meta": {},
        "evaluator_feedback": "",
        "attempt_count": 0,
        "playwright_available": playwright_available,
        "pdf_bytes": None,
        "pdf_filename": None,
        "launch_requested": False,
        "open_report_requested": False,
        "cancel_requested": False,
    }
    prefs = load_preferences()
    defaults["preferences"] = prefs

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "app" not in st.session_state:
        from services.deepsearch_app import DeepSearchApp

        st.session_state.app = DeepSearchApp()


def set_view(view: str) -> None:
    if view in VIEWS:
        st.session_state.view = view


def reset_search_state() -> None:
    st.session_state.live_steps = []
    st.session_state.sources = []
    st.session_state.running = False
    st.session_state.done = False
    st.session_state.elapsed_ms = 0
    st.session_state.search_started = False
    st.session_state.current_run_id = None
    st.session_state.report_content = ""
    st.session_state.report_meta = {}
    st.session_state.evaluator_feedback = ""
    st.session_state.attempt_count = 0
    st.session_state.pdf_bytes = None
    st.session_state.pdf_filename = None
    st.session_state.launch_requested = False
    st.session_state.open_report_requested = False
    st.session_state.cancel_requested = False
    st.session_state.pop("search_progress", None)
    st.session_state.pop("_search_result_applied", None)


def load_history_entry_to_session(entry: dict) -> None:
    st.session_state.query = entry.get("query", "")
    st.session_state.criteria = entry.get("criteria", "")
    st.session_state.report_content = entry.get("report_content", "")
    st.session_state.sources = entry.get("sources", [])
    st.session_state.report_meta = {
        "duration_s": entry.get("duration_s", 0),
        "sources_count": entry.get("sources_count", 0),
        "attempt_count": entry.get("attempt_count", 1),
        "status": entry.get("status", "done"),
        "started_at": entry.get("started_at", ""),
    }
    st.session_state.done = True
    st.session_state.running = False
    st.session_state.pdf_bytes = None
    st.session_state.pdf_filename = None
    st.session_state.view = "report"
