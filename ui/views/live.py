from __future__ import annotations

import time

import streamlit as st

from services.live_search_progress import start_search_thread
from services.search_runner import SearchSession, fmt_elapsed, progress_pct
from ui.state import reset_search_state, set_view
from ui.views.components import render_sources_html, render_timeline_html


def _is_failed_search() -> bool:
    content = (st.session_state.report_content or "").strip()
    status = (st.session_state.report_meta or {}).get("status")
    return status == "failed" or content.lower().startswith("erreur")


def _render_live_ui() -> None:
    steps = st.session_state.live_steps
    sources = st.session_state.sources
    elapsed = st.session_state.elapsed_ms
    running = st.session_state.running and not st.session_state.done
    done = st.session_state.done
    failed = done and _is_failed_search()
    pct = progress_pct(steps)

    if running:
        status_label = "Recherche en cours"
    elif failed:
        status_label = "Échec de la recherche"
    elif done:
        status_label = "Recherche terminée"
    else:
        status_label = "En attente"

    dot_class = "ds-live-dot" if running else "ds-live-dot ds-live-dot-done"
    if failed:
        dot_class = "ds-live-dot ds-live-dot-done"

    head_left, head_right = st.columns([3, 1])
    with head_left:
        st.markdown(
            f'<div class="ds-live-badge"><span class="{dot_class}"></span>'
            f'<span style="font:600 12px/1 IBM Plex Sans,sans-serif;color:#9A4A2B">{status_label}</span>'
            f'<span style="font:500 12px/1 IBM Plex Mono,monospace;color:#B07254;border-left:1px solid #E2C4B5;'
            f'padding-left:9px;margin-left:2px">{fmt_elapsed(elapsed)}</span></div>'
            f'<h1 style="font:500 27px/1.3 Newsreader,serif;color:#1A211E;margin:0 0 8px">'
            f"{st.session_state.query}</h1>",
            unsafe_allow_html=True,
        )
    with head_right:
        if done and not failed and st.button(
            "Ouvrir le rapport →", type="primary", key="open_report", use_container_width=True
        ):
            set_view("report")
            st.rerun()
        if done and failed and st.button(
            "Voir le détail →", type="primary", key="open_failed_report", use_container_width=True
        ):
            set_view("report")
            st.rerun()
        if st.button("Annuler", key="cancel_search", use_container_width=True):
            reset_search_state()
            set_view("home")
            st.rerun()

    st.markdown(
        f'<div class="ds-progress"><div class="ds-progress-bar" style="width:{pct}%"></div></div>',
        unsafe_allow_html=True,
    )

    if failed and st.session_state.report_content:
        st.error(st.session_state.report_content[:500])

    col_timeline, col_sources = st.columns([2, 1])
    with col_timeline:
        st.markdown(render_timeline_html(steps), unsafe_allow_html=True)
    with col_sources:
        st.markdown(
            f'<div class="ds-panel">{render_sources_html(sources)}</div>',
            unsafe_allow_html=True,
        )
        if done and not failed:
            feedback = (st.session_state.evaluator_feedback or "Critères de succès vérifiés.")[:280]
            st.markdown(
                f'<div class="ds-panel-dark" style="margin-top:16px">'
                f'<div style="display:flex;align-items:center;gap:9px;margin-bottom:10px">'
                f'<span style="color:#1F8A5B;font-size:18px">✓</span>'
                f'<span style="font:600 13px/1 Space Grotesk,sans-serif;color:#EAF3EE">'
                f"Évaluateur — critères remplis</span></div>"
                f'<div style="font:400 12.5px/1.55 IBM Plex Sans,sans-serif;color:#9DB4AA">{feedback}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _apply_search_result(result: dict) -> None:
    app = st.session_state.app
    st.session_state.live_steps = result["steps"]
    st.session_state.sources = result["sources"]
    st.session_state.report_content = result["report_content"]
    st.session_state.evaluator_feedback = result.get("evaluator_feedback", "")
    st.session_state.attempt_count = result["attempt_count"]
    st.session_state.report_meta = {
        "duration_s": result["duration_s"],
        "duration_label": result["duration_label"],
        "sources_count": len(result["sources"]),
        "attempt_count": result["attempt_count"],
        "status": result["status"],
        "history_id": result["history_id"],
    }
    st.session_state.running = False
    st.session_state.done = True
    st.session_state.elapsed_ms = max(st.session_state.elapsed_ms, result["duration_s"] * 1000)

    prefs = st.session_state.preferences
    if prefs.get("auto_pdf") and result["report_content"] and result["status"] == "done":
        pdf_bytes, filename = app.generate_pdf_report(
            st.session_state.query,
            result["report_content"],
            duration_s=result["duration_s"],
            sources_count=len(result["sources"]),
            attempt_count=result["attempt_count"],
        )
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_filename = filename

    if prefs.get("notify") and result["report_content"] and result["status"] == "done":
        app.send_pushover_report(
            st.session_state.query,
            result["report_content"],
            duration_s=result["duration_s"],
            sources_count=len(result["sources"]),
        )


def _sync_progress_to_session(progress) -> None:
    snap = progress.snapshot()
    st.session_state.live_steps = snap["steps"] or st.session_state.live_steps
    st.session_state.sources = snap["sources"]
    st.session_state.elapsed_ms = snap["elapsed_ms"]
    st.session_state.running = snap["running"]
    st.session_state.done = snap["done"]

    if snap["error"] and snap["done"] and not st.session_state.get("_search_result_applied"):
        st.session_state.report_content = f"Erreur : {snap['error']}"
        st.session_state.report_meta = {"status": "failed", "duration_s": max(1, snap["elapsed_ms"] // 1000)}
        st.session_state.running = False
        st.session_state.done = True
        st.session_state._search_result_applied = True
        return

    if snap["result"] and snap["done"] and not st.session_state.get("_search_result_applied"):
        _apply_search_result(snap["result"])
        st.session_state._search_result_applied = True


def render_live() -> None:
    if st.session_state.launch_requested and not st.session_state.search_started:
        st.session_state.launch_requested = False
        st.session_state.search_started = True
        st.session_state.running = True
        st.session_state.done = False
        st.session_state._search_result_applied = False
        st.session_state.search_progress = start_search_thread(
            app=st.session_state.app,
            query=st.session_state.query,
            criteria=st.session_state.criteria,
            playwright_available=st.session_state.playwright_available,
        )

    progress = st.session_state.get("search_progress")
    if progress is not None:
        _sync_progress_to_session(progress)

    _render_live_ui()

    if st.session_state.running and not st.session_state.done:
        time.sleep(0.6)
        st.rerun()


def build_initial_steps_safe() -> list:
    return SearchSession(playwright_available=st.session_state.playwright_available).steps
