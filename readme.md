# 🔍 DeepSearch - Outil de Recherche Approfondie

Une application de recherche intelligente utilisant l'IA pour effectuer des recherches approfondies et générer des rapports PDF avec notifications push.

## 🎮 Démo

**Essayez l'application en ligne :** [DeepSearch Cloud](https://deepsearch-langchain-ai.streamlit.app/)

> 💡 **Note :** La version démo utilise les fonctionnalités cloud (sans Playwright). Pour une utilisation complète, installez l'application localement.

## ✨ Fonctionnalités

- **🔍 Recherche Intelligente**: Utilise GPT-4 et des outils avancés pour des recherches approfondies
- **📄 Rapports PDF**: Génération automatique de rapports professionnels
- **📱 Notifications Push**: Envoi de notifications via Pushover avec le rapport en pièce jointe
- **🌐 Navigation Web**: Navigation automatique et extraction d'informations web
- **🐍 Exécution Python**: Capacité d'exécuter du code Python pour l'analyse
- **📚 Sources Multiples**: Recherche Google, Wikipedia, et navigation web

## 🚀 Installation

### Installation automatique (Recommandée)
```bash
python install.py
```

### Installation manuelle

1. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

2. **Installer Playwright** (pour la navigation web)
```bash
playwright install
```

3. **Configuration des variables d'environnement**

Copiez le fichier d'exemple et configurez vos clés:
```bash
cp config_example.env .env
```

Puis éditez `.env` avec vos vraies valeurs:
```env
# Obligatoire
OPENAI_API_KEY=votre_clé_openai

# Optionnel pour les recherches web
SERPER_API_KEY=votre_clé_serper

# Optionnel pour les notifications Pushover
PUSHOVER_TOKEN=votre_token_pushover
PUSHOVER_USER=votre_user_pushover
```

4. **Tester la configuration**
```bash
python test_setup.py
```

5. **Tester les outils (optionnel)**
```bash
python test_tools.py
```

6. **Tester Pushover (optionnel)**
```bash
python test_pushover.py
```

## 🎯 Utilisation

### Interface Streamlit Locale (Recommandée)
```bash
python run_deepsearch.py
```
ou
```bash
streamlit run streamlit_app.py
```

### Interface Streamlit Cloud
```bash
streamlit run app_streamlit_cloud.py
```

### Interface Gradio (Legacy)
```bash
python app.py
```

## 🚀 Déploiement Streamlit Cloud

Votre application est prête pour le déploiement sur Streamlit Cloud !

**Fichiers de déploiement :**
- `app_streamlit_cloud.py` - Version optimisée pour le cloud
- `requirements_streamlit.txt` - Dépendances cloud
- `packages.txt` - Dépendances système
- `DEPLOYMENT.md` - Guide complet de déploiement

**Étapes rapides :**
1. Pushez votre code sur GitHub
2. Allez sur [share.streamlit.io](https://share.streamlit.io)
3. Sélectionnez `app_streamlit_cloud.py` comme fichier principal
4. Configurez vos secrets API dans Settings > Secrets

📖 **Guide complet :** Consultez `DEPLOYMENT.md` pour les instructions détaillées.
📋 **Guide d'utilisation :** Consultez `GUIDE_UTILISATION.md` pour optimiser vos recherches.

## 📱 Configuration Pushover

1. Créez un compte sur [Pushover](https://pushover.net/)
2. Créez une application pour obtenir votre token
3. Notez votre User Key
4. Ajoutez ces informations dans votre fichier `.env`

## 🔧 Structure du Projet

- `streamlit_app.py` - Application Streamlit principale
- `app.py` - Interface Gradio (legacy)
- `sidekick.py` - Moteur de recherche principal
- `sidekick_tools.py` - Outils et intégrations
- `run_deepsearch.py` - Script de lancement

## 📋 Exemple d'Utilisation

1. **Lancez l'application**: `python run_deepsearch.py`
2. **Entrez votre recherche**: "Analysez les tendances du marché crypto en 2024"
3. **Définissez vos critères**: "Je veux un rapport détaillé avec des sources fiables"
4. **Cliquez sur "Lancer la recherche"**
5. **Recevez votre rapport PDF par notification push**

## 🛠️ Dépannage

### Problèmes courants

**Erreur Playwright**: Exécutez `playwright install`
**Erreur OpenAI**: Vérifiez votre clé API dans `.env`
**Notifications non reçues**: Vérifiez vos tokens Pushover
**Erreur BeautifulSoup**: Exécutez `python -m pip install beautifulsoup4 lxml`
**Erreur Wikipedia**: Exécutez `python -m pip install wikipedia`
**Erreur de récursion**: L'application a une limite de 8 tentatives pour éviter les boucles infinies
**Erreur tool_calls**: L'application gère automatiquement les erreurs d'outils et propose des alternatives

### Logs

L'application affiche des informations détaillées dans la console pour le débogage.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
