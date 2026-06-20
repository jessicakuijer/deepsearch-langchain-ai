"""Point d'entrée Streamlit DeepSearch."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    from sidekick_tools import PLAYWRIGHT_AVAILABLE
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _sync_secrets_to_env() -> None:
    try:
        for key in (
            "OPENAI_API_KEY",
            "SERPER_API_KEY",
            "PUSHOVER_TOKEN",
            "PUSHOVER_USER",
            "OPENAI_MODEL",
        ):
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


from ui.layout import render_shell
from ui.state import init_session_state
from ui.styles import inject_design_system
from ui.views.history import render_history
from ui.views.home import render_home
from ui.views.live import render_live
from ui.views.report import render_report
from ui.views.settings import render_settings


def render_main() -> None:
    view = st.session_state.view
    if view == "home":
        render_home()
    elif view == "live":
        render_live()
    elif view == "report":
        render_report()
    elif view == "history":
        render_history()
    elif view == "settings":
        render_settings()
    else:
        render_home()


def main() -> None:
    st.set_page_config(
        page_title="DeepSearch - Recherche Approfondie",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_design_system()
    _sync_secrets_to_env()
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Clé API OpenAI manquante. Configurez OPENAI_API_KEY dans `.env` ou les secrets Streamlit.")
        st.stop()
    init_session_state(playwright_available=PLAYWRIGHT_AVAILABLE)
    render_shell(render_main)


if __name__ == "__main__":
    main()
