from __future__ import annotations

import streamlit as st

from ui.history_store import format_duration, format_relative_time, load_history
from ui.state import load_history_entry_to_session


def render_history() -> None:
    entries = load_history()

    st.markdown(
        '<h1 class="ds-h1-sm">Historique</h1>'
        '<p class="ds-sublead">Vos recherches passées et leurs rapports.</p>',
        unsafe_allow_html=True,
    )

    if not entries:
        st.markdown('<div class="ds-empty">Aucune recherche enregistrée pour le moment.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ds-list-card-wrap">', unsafe_allow_html=True)
        for entry in entries:
            ok = entry.get("status") == "done"
            status_label = "Terminé" if ok else "À revoir"
            status_color = "#0F6B54" if ok else "#9A4A2B"
            status_bg = "#E9F1ED" if ok else "#F7E9E1"
            when = format_relative_time(entry.get("started_at", ""))
            meta = f"{entry.get('sources_count', 0)} sources · {format_duration(entry.get('duration_s', 0))}"

            st.markdown('<div class="ds-list-btn">', unsafe_allow_html=True)
            if st.button(entry.get("query", "Sans titre")[:90], key=f"hist_{entry.get('id')}", use_container_width=True):
                load_history_entry_to_session(entry)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:0 18px 14px;margin-top:-6px">'
                f'<span style="font-size:12px;color:#9AA39C">{when}</span>'
                f'<span style="width:3px;height:3px;border-radius:50%;background:#CCD3CC"></span>'
                f'<span style="font-size:12px;color:#9AA39C">{meta}</span>'
                f'<span style="margin-left:auto;font:500 11px/1 IBM Plex Sans,sans-serif;color:{status_color};'
                f'background:{status_bg};padding:5px 10px;border-radius:7px">{status_label}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
