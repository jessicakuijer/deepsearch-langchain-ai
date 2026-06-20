from __future__ import annotations

from datetime import datetime

import streamlit as st

from ui.history_store import format_duration
from ui.report_format import TableSegment, parse_report_segments, render_table_cards
from ui.state import reset_search_state, set_view
from ui.views.components import render_report_sources_html


def render_report() -> None:
    meta = st.session_state.report_meta or {}
    duration_label = meta.get("duration_label") or format_duration(meta.get("duration_s", 0))
    sources_count = meta.get("sources_count", len(st.session_state.sources))
    attempt_count = meta.get("attempt_count", st.session_state.attempt_count or 1)
    started_at = meta.get("started_at")
    date_label = (
        datetime.fromisoformat(started_at.replace("Z", "+00:00")).strftime("%d %B %Y")
        if started_at
        else datetime.now().strftime("%d %B %Y")
    )

    st.markdown('<span id="ds-report-view"></span>', unsafe_allow_html=True)

    if st.button("← Nouvelle recherche", key="report_back"):
        reset_search_state()
        set_view("home")
        st.rerun()

    col_article, col_side = st.columns([2, 1])
    with col_article:
        st.markdown('<div class="ds-label" style="margin-bottom:18px">RAPPORT DE RECHERCHE</div>', unsafe_allow_html=True)
        st.markdown(f"## {st.session_state.query}")
        st.markdown(
            f'<div class="ds-meta-grid">'
            f'<div><div class="ds-meta-label">DATE</div><div class="ds-meta-value">{date_label}</div></div>'
            f'<div><div class="ds-meta-label">DURÉE</div><div class="ds-meta-value">{duration_label}</div></div>'
            f'<div><div class="ds-meta-label">SOURCES</div><div class="ds-meta-value">{sources_count} références</div></div>'
            f'<div><div class="ds-meta-label">TENTATIVES</div><div class="ds-meta-value">{attempt_count}</div></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        for segment in parse_report_segments(st.session_state.report_content):
            if isinstance(segment, TableSegment):
                st.markdown(render_table_cards(segment.headers, segment.rows), unsafe_allow_html=True)
            else:
                st.markdown(segment.content)

    with col_side:
        st.markdown('<span id="ds-report-actions"></span>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                '<div class="ds-section-label" style="color:#7FA395;margin-bottom:14px">ACTIONS</div>',
                unsafe_allow_html=True,
            )
            app = st.session_state.app

            if st.session_state.pdf_bytes is None and st.session_state.report_content:
                pdf_bytes, filename = app.generate_pdf_report(
                    st.session_state.query,
                    st.session_state.report_content,
                    duration_s=meta.get("duration_s", 0),
                    sources_count=sources_count,
                    attempt_count=attempt_count,
                )
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_filename = filename

            if st.session_state.pdf_bytes:
                st.download_button(
                    "Télécharger le PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_filename or "rapport_deepsearch.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_pdf",
                )

            if st.button("Envoyer en notification", use_container_width=True, key="send_push"):
                ok, msg = app.send_pushover_report(
                    st.session_state.query,
                    st.session_state.report_content,
                    duration_s=meta.get("duration_s", 0),
                    sources_count=sources_count,
                )
                st.success(msg) if ok else st.warning(msg)

            if st.button("Copier le texte", use_container_width=True, key="copy_text"):
                st.text_area(
                    "Contenu",
                    value=st.session_state.report_content,
                    height=200,
                    label_visibility="collapsed",
                    key="copy_area",
                )
                st.caption("Sélectionnez le texte ci-dessus pour copier.")

        st.markdown(
            f'<div class="ds-panel ds-report-sources">'
            f'<div class="ds-section-label">SOURCES & FIABILITÉ</div>'
            f"{render_report_sources_html(st.session_state.sources)}"
            f"</div>",
            unsafe_allow_html=True,
        )
