from pathlib import Path

import streamlit as st


def inject_design_system() -> None:
    css_path = Path(__file__).parent / "design_system.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
