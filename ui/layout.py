"""Shell layout : sidebar navigation et widget état système."""

from __future__ import annotations

import os

import streamlit as st

from ui.state import set_view


def _env_or_secret(key: str) -> str | None:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def get_system_status() -> dict:
    openai_ok = bool(_env_or_secret("OPENAI_API_KEY"))
    serper_ok = bool(_env_or_secret("SERPER_API_KEY"))
    pushover_ok = bool(_env_or_secret("PUSHOVER_TOKEN") and _env_or_secret("PUSHOVER_USER"))
    worker_model = _env_or_secret("OPENAI_MODEL") or "gpt-5.5"
    return {
        "openai_ok": openai_ok,
        "serper_ok": serper_ok,
        "pushover_ok": pushover_ok,
        "worker_model": worker_model,
    }


def _status_rows_html(status: dict) -> str:
    rows = [
        ("OpenAI", f"· {status['worker_model']}", status["openai_ok"]),
        ("Serper", "· Web", status["serper_ok"]),
        ("Pushover", "· notif.", status["pushover_ok"]),
    ]
    parts = []
    for label, suffix, ok in rows:
        dot = "ds-dot-ok" if ok else "ds-dot-warn"
        parts.append(
            f'<div class="ds-status-row"><span class="ds-dot {dot}"></span>{label} {suffix}</div>'
        )
    return "".join(parts)


def render_sidebar_nav() -> None:
    current = st.session_state.get("view", "home")
    status = get_system_status()

    st.markdown(
        '<div class="ds-brand">'
        '<div class="ds-brand-icon">'
        '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#EAF3EE" stroke-width="2" stroke-linecap="round">'
        '<circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path>'
        "</svg></div>"
        '<div><div class="ds-brand-title" style="color:#FFFFFF!important">DeepSearch</div>'
        '<div class="ds-brand-sub" style="color:#A8B5AE!important">RECHERCHE APPROFONDIE</div></div></div>',
        unsafe_allow_html=True,
    )

    nav_items = [
        ("home", "Nouvelle recherche"),
        ("history", "Historique"),
        ("settings", "Paramètres"),
    ]
    icons = {"home": "＋", "history": "↺", "settings": "⚙"}

    for view_id, label in nav_items:
        active = current == view_id
        if st.button(
            f"{icons[view_id]}  {label}",
            key=f"nav_{view_id}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            if view_id == "home":
                from ui.state import reset_search_state

                reset_search_state()
            set_view(view_id)
            st.rerun()

    st.markdown(
        f'<div class="ds-status-box"><div class="ds-status-label">ÉTAT DU SYSTÈME</div>'
        f"{_status_rows_html(status)}</div>"
        '<div style="display:flex;align-items:center;gap:10px;padding:4px 8px;margin-top:14px">'
        '<div style="width:30px;height:30px;border-radius:50%;background:#2C3D36;display:flex;'
        'align-items:center;justify-content:center;font:600 12px/1 Space Grotesk,sans-serif;color:#9FB0A8">DS</div>'
        '<div><div style="font:600 12.5px/1 IBM Plex Sans,sans-serif;color:#E4EAE6">Espace de travail</div>'
        '<div style="font:400 11px/1.3 IBM Plex Sans,sans-serif;color:#76857E">Plan personnel</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_shell(main_renderer) -> None:
    st.markdown('<span id="ds-app-shell"></span>', unsafe_allow_html=True)
    side_col, main_col = st.columns([1, 5], gap="small")

    with side_col:
        render_sidebar_nav()

    with main_col:
        main_renderer()
