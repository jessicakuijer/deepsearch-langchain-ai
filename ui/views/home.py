from __future__ import annotations

import streamlit as st

from ui.history_store import format_relative_time, get_recent_history
from ui.state import reset_search_state, set_view
from ui.views.constants import EXAMPLES


def render_home() -> None:
    st.markdown(
        '<div class="ds-badge"><span class="ds-badge-dot"></span>'
        '<span class="ds-badge-text">Agent de recherche autonome</span></div>'
        '<h1 class="ds-h1">Posez une question.<br>Recevez un rapport sourcé.</h1>'
        '<p class="ds-lead">L\'agent parcourt le web, Wikipédia et exécute du code pour répondre à vos critères, '
        "puis rédige un rapport PDF complet.</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="ds-label">VOTRE RECHERCHE</div>', unsafe_allow_html=True)
        query = st.text_area(
            "query",
            value=st.session_state.query,
            placeholder="Ex. Quels sont les meilleurs restaurants à Meaux ?",
            height=72,
            label_visibility="collapsed",
            key="home_query",
        )
        st.session_state.query = query

        st.markdown('<div class="ds-form-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="ds-label">CRITÈRES DE SUCCÈS</div>', unsafe_allow_html=True)
        criteria = st.text_input(
            "criteria",
            value=st.session_state.criteria,
            placeholder="Ce qui rendrait la réponse satisfaisante (sources, format, niveau de détail…)",
            label_visibility="collapsed",
            key="home_criteria",
        )
        st.session_state.criteria = criteria

        browser_badge = (
            '<span class="ds-tool-badge">Navigateur</span>'
            if st.session_state.playwright_available
            else '<span class="ds-tool-badge" style="opacity:.55">Navigateur (indisponible)</span>'
        )
        st.markdown(
            '<div class="ds-tool-badges">'
            '<span class="ds-tool-badge">Web</span>'
            '<span class="ds-tool-badge">Wikipédia</span>'
            f"{browser_badge}"
            '<span class="ds-tool-badge">Python</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<span id="ds-launch"></span>', unsafe_allow_html=True)
    if st.button("Lancer la recherche →", type="primary", use_container_width=False, key="launch_search"):
        if not (query or "").strip():
            st.warning("Veuillez entrer une requête.")
        else:
            reset_search_state()
            st.session_state.query = query.strip()
            st.session_state.criteria = (criteria or "").strip()
            st.session_state.launch_requested = True
            st.session_state.view = "live"
            st.rerun()

    st.markdown('<div class="ds-section-label" style="margin-top:38px">EXEMPLES</div>', unsafe_allow_html=True)
    st.markdown('<span id="ds-examples"></span>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(ex["q"], key=f"example_{i}", use_container_width=True):
                st.session_state.query = ex["q"]
                st.session_state.criteria = ex["c"]
                st.rerun()
            st.caption(ex["c"])

    st.markdown(
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:34px;margin-bottom:12px">'
        '<div class="ds-section-label" style="margin:0">RECHERCHES RÉCENTES</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Tout voir →", key="see_all_history"):
        set_view("history")
        st.rerun()

    recent = get_recent_history(3)
    if recent:
        st.markdown('<div class="ds-list-card-wrap">', unsafe_allow_html=True)
        for entry in recent:
            when = format_relative_time(entry.get("started_at", ""))
            st.markdown('<div class="ds-list-btn">', unsafe_allow_html=True)
            if st.button(
                f"{entry.get('query', '')[:70]}",
                key=f"recent_{entry.get('id')}",
                use_container_width=True,
            ):
                from ui.state import load_history_entry_to_session

                load_history_entry_to_session(entry)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:12px;color:#9AA39C;padding:0 18px 12px;margin-top:-8px">{when}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="ds-empty">Aucune recherche récente pour le moment.</div>',
            unsafe_allow_html=True,
        )
