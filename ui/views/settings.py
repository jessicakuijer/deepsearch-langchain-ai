from __future__ import annotations

import streamlit as st

from ui.history_store import load_preferences, save_preferences
from ui.layout import get_system_status


def render_settings() -> None:
    status = get_system_status()
    prefs = st.session_state.preferences

    st.markdown(
        '<h1 class="ds-h1-sm">Paramètres</h1>'
        '<p class="ds-sublead">Clés d\'API et préférences de l\'agent.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ds-section-label">CONNEXIONS</div>', unsafe_allow_html=True)

    def pill(ok: bool) -> str:
        if ok:
            return (
                '<span class="ds-status-pill ds-status-pill-ok">'
                '<span class="ds-dot ds-dot-ok" style="width:6px;height:6px"></span>Connecté</span>'
            )
        return (
            '<span class="ds-status-pill ds-status-pill-warn">'
            '<span class="ds-dot ds-dot-warn" style="width:6px;height:6px"></span>Non configuré</span>'
        )

    st.markdown(
        f'<div class="ds-settings-card"><div style="flex:1"><div style="font:600 14px/1.3 IBM Plex Sans,sans-serif;color:#1F2823">'
        f'OpenAI</div><div style="font:400 12.5px/1.4 IBM Plex Sans,sans-serif;color:#8A938D;margin-top:2px">'
        f"Modèle worker · {status['worker_model']}</div></div>{pill(status['openai_ok'])}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ds-settings-card"><div style="flex:1"><div style="font:600 14px/1.3 IBM Plex Sans,sans-serif;color:#1F2823">'
        f'Serper</div><div style="font:400 12.5px/1.4 IBM Plex Sans,sans-serif;color:#8A938D;margin-top:2px">'
        f"Recherche Google web</div></div>{pill(status['serper_ok'])}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ds-settings-card" style="flex-direction:column;align-items:stretch">'
        f'<div style="display:flex;align-items:center;gap:14px">'
        f'<div style="flex:1"><div style="font:600 14px/1.3 IBM Plex Sans,sans-serif;color:#1F2823">Pushover</div>'
        f'<div style="font:400 12.5px/1.4 IBM Plex Sans,sans-serif;color:#8A938D;margin-top:2px">'
        f"Notifications push avec le rapport en texte</div></div>{pill(status['pushover_ok'])}</div>"
        f'<p style="font-size:12.5px;color:#8A938D;margin:10px 0 0">Configurez '
        f"<code>PUSHOVER_TOKEN</code> et <code>PUSHOVER_USER</code> dans <code>.env</code> "
        f"ou les secrets Streamlit.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ds-section-label" style="margin-top:24px">PRÉFÉRENCES</div>', unsafe_allow_html=True)
    auto_pdf = st.checkbox("Générer un PDF automatiquement", value=prefs.get("auto_pdf", True), key="pref_auto_pdf")
    notify = st.checkbox("Notification à la fin de la recherche", value=prefs.get("notify", True), key="pref_notify")
    lang = st.selectbox("Langue des rapports", ["Français", "English"], index=0 if prefs.get("lang") == "fr" else 1)

    if st.button("Enregistrer les préférences", type="primary"):
        save_preferences(
            {
                "auto_pdf": auto_pdf,
                "notify": notify,
                "lang": "fr" if lang == "Français" else "en",
            }
        )
        st.session_state.preferences = load_preferences()
        st.success("Préférences enregistrées.")
