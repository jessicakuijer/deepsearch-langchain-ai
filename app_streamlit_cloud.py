import streamlit as st
import asyncio
import os
from datetime import datetime
from sidekick import Sidekick
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
import requests
from io import BytesIO
import tempfile


class DeepSearchCloudApp:
    def __init__(self):
        self.sidekick = None
        self.pushover_token = None
        self.pushover_user = None
        self.pushover_url = "https://api.pushover.net/1/messages.json"

    async def initialize_sidekick(self):
        """Initialise le sidekick de manière asynchrone"""
        if self.sidekick is None:
            self.sidekick = Sidekick()
            await self.sidekick.setup()
        return self.sidekick

    def generate_pdf_report(self, query, results, filename="rapport.pdf"):
        """Génère un rapport PDF avec les résultats de la recherche"""
        
        # Créer un buffer en mémoire pour Streamlit Cloud
        buffer = BytesIO()
        
        # Créer le document PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
        )
        
        # Contenu du rapport
        story = []
        
        # Titre
        story.append(Paragraph("Rapport de Recherche Approfondie", title_style))
        story.append(Spacer(1, 12))
        
        # Informations générales
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", body_style))
        story.append(Paragraph(f"Requête: {query}", body_style))
        story.append(Spacer(1, 20))
        
        # Résultats
        story.append(Paragraph("Résultats de la Recherche", subtitle_style))
        
        # Traiter les résultats
        if isinstance(results, list):
            for result in results:
                if hasattr(result, 'content'):
                    content = result.content
                elif isinstance(result, dict) and 'content' in result:
                    content = result['content']
                else:
                    content = str(result)
                
                if content and content.strip():
                    clean_content = content.replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(clean_content, body_style))
                    story.append(Spacer(1, 12))
        else:
            clean_results = str(results).replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(clean_results, body_style))
        
        # Construire le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer

    def send_pushover_notification(self, message, title="Rapport DeepSearch"):
        """Envoie une notification Pushover avec le contenu textuel"""
        if not self.pushover_token or not self.pushover_user:
            return False, "Tokens Pushover non configurés"
        
        data = {
            "token": self.pushover_token,
            "user": self.pushover_user,
            "message": message,
            "title": title,
            "priority": 0  # Priorité normale
        }
        
        try:
            response = requests.post(self.pushover_url, data=data)
            if response.status_code == 200:
                return True, "Notification envoyée avec succès"
            else:
                return False, f"Erreur: {response.status_code}"
        except Exception as e:
            return False, f"Erreur lors de l'envoi: {str(e)}"

    def extract_main_content(self, results):
        """Extrait le contenu principal des résultats pour la notification"""
        main_content = ""
        for result in results:
            if isinstance(result, dict) and 'content' in result:
                content = result['content']
                role = result.get('role', 'assistant')
                
                if role == 'assistant' and "Evaluator Feedback" not in content:
                    # Prendre seulement le contenu principal, pas l'évaluation
                    main_content = content[:1000] + "..." if len(content) > 1000 else content
                    break
        
        return main_content or "Recherche terminée - consultez le rapport complet."

    def initialize_pushover_config(self):
        """Initialise la configuration Pushover depuis les secrets"""
        try:
            self.pushover_token = st.secrets.get("PUSHOVER_TOKEN")
            self.pushover_user = st.secrets.get("PUSHOVER_USER")
            return bool(self.pushover_token and self.pushover_user)
        except:
            return False

    async def process_search(self, query, success_criteria):
        """Traite la recherche et retourne les résultats"""
        sidekick = await self.initialize_sidekick()
        results = await sidekick.run_superstep(query, success_criteria, [])
        return results


def main():
    st.set_page_config(
        page_title="DeepSearch - Recherche Approfondie",
        page_icon="🔍",
        layout="wide"
    )
    
    # CSS personnalisé
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #2E86C1;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .search-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .result-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #2E86C1;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialiser l'application
    if 'app' not in st.session_state:
        st.session_state.app = DeepSearchCloudApp()
    
    # Titre principal
    st.markdown('<h1 class="main-header">🔍 DeepSearch - Recherche Approfondie</h1>', unsafe_allow_html=True)
    
    # Vérification des variables d'environnement
    if not st.secrets.get("OPENAI_API_KEY"):
        st.error("❌ Clé API OpenAI manquante. Configurez OPENAI_API_KEY dans les secrets Streamlit.")
        st.info("Allez dans Settings > Secrets pour configurer vos clés API.")
        st.stop()
    
    # Interface de recherche
    with st.container():
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            query = st.text_area(
                "Votre recherche:",
                placeholder="Entrez votre requête de recherche ici...",
                height=100,
                help="Décrivez ce que vous souhaitez rechercher en détail"
            )
        
        with col2:
            success_criteria = st.text_area(
                "Critères de succès:",
                placeholder="Quels sont vos critères de réussite?",
                height=100,
                help="Définissez ce qui constituerait une réponse satisfaisante"
            )
        
        # Options
        st.subheader("📋 Options")
        col3, col4 = st.columns(2)
        
        with col3:
            generate_pdf = st.checkbox("Générer un rapport PDF", value=True)
            send_notification = st.checkbox("Envoyer notification push", value=False)
        
        with col4:
            # Vérifier la configuration Pushover
            pushover_configured = st.session_state.app.initialize_pushover_config()
            if send_notification:
                if pushover_configured:
                    st.success("✅ Pushover configuré")
                else:
                    st.error("❌ Pushover non configuré")
                    st.info("Configurez PUSHOVER_TOKEN et PUSHOVER_USER dans les secrets")
                    send_notification = False
        
        # Bouton de recherche
        search_button = st.button("🚀 Lancer la recherche", type="primary", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Traitement de la recherche
    if search_button and query:
        if not success_criteria:
            success_criteria = "La réponse doit être claire, précise et complète"
        
        with st.spinner("🔍 Recherche en cours... Cela peut prendre quelques minutes."):
            try:
                # Exécuter la recherche
                results = asyncio.run(st.session_state.app.process_search(query, success_criteria))
                
                # Afficher les résultats
                st.markdown('<div class="result-container">', unsafe_allow_html=True)
                st.subheader("📊 Résultats de la recherche")
                
                # Afficher chaque message des résultats
                for result in results:
                    if isinstance(result, dict) and 'content' in result:
                        content = result['content']
                        role = result.get('role', 'assistant')
                        
                        if role == 'user':
                            st.markdown(f"**👤 Utilisateur:** {content}")
                        elif role == 'assistant':
                            if "Evaluator Feedback" in content:
                                st.markdown(f"**🤖 Évaluation:** {content}")
                            else:
                                st.markdown(f"**🎯 Réponse:** {content}")
                        
                        st.markdown("---")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Actions post-recherche
                actions_completed = []
                
                # Génération du PDF
                if generate_pdf:
                    try:
                        pdf_buffer = st.session_state.app.generate_pdf_report(query, results)
                        
                        # Téléchargement du PDF
                        st.download_button(
                            label="📥 Télécharger le rapport PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"rapport_deepsearch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                        actions_completed.append("PDF généré")
                    except Exception as e:
                        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
                
                # Envoi de notification push
                if send_notification and pushover_configured:
                    try:
                        # Extraire le contenu principal pour la notification
                        main_content = st.session_state.app.extract_main_content(results)
                        notification_message = f"Recherche terminée: {query[:50]}...\n\n{main_content}"
                        
                        success, msg = st.session_state.app.send_pushover_notification(
                            notification_message,
                            "DeepSearch - Résultats"
                        )
                        
                        if success:
                            actions_completed.append("Notification envoyée")
                        else:
                            st.warning(f"Notification non envoyée: {msg}")
                    except Exception as e:
                        st.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
                
                # Message de succès global
                if actions_completed:
                    success_msg = f"✅ Recherche terminée! Actions complétées: {', '.join(actions_completed)}"
                    st.markdown(f'<div class="success-message">{success_msg}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="success-message">✅ Recherche terminée!</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.markdown(f'<div class="error-message">❌ Erreur lors de la recherche: {str(e)}</div>', unsafe_allow_html=True)
    
    elif search_button and not query:
        st.warning("⚠️ Veuillez entrer une requête de recherche")
    
    # Sidebar avec informations
    with st.sidebar:
        st.header("ℹ️ Informations")
        st.markdown("""
        **DeepSearch Cloud** utilise l'intelligence artificielle pour effectuer des recherches approfondies.
        
        **Fonctionnalités:**
        - 🔍 Recherche intelligente multi-sources
        - 📄 Génération de rapports PDF
        - 📱 Notifications push via Pushover
        - 🐍 Exécution de code Python
        - 📚 Recherche Wikipedia et Google
        
        **Note:** Navigation web désactivée sur Streamlit Cloud.
        """)
        
        st.header("🛠️ État du système")
        if st.secrets.get("OPENAI_API_KEY"):
            st.success("✅ OpenAI configuré")
        else:
            st.error("❌ OpenAI non configuré")
        
        if st.secrets.get("SERPER_API_KEY"):
            st.success("✅ Serper API configuré")
        else:
            st.warning("⚠️ Serper API non configuré")
        
        if st.secrets.get("PUSHOVER_TOKEN") and st.secrets.get("PUSHOVER_USER"):
            st.success("✅ Pushover configuré")
        else:
            st.warning("⚠️ Pushover non configuré")


if __name__ == "__main__":
    main()
