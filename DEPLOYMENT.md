# 🚀 Guide de Déploiement Streamlit Cloud

## 📋 Préparation

### 1. Fichiers nécessaires pour le déploiement

- ✅ `app_streamlit_cloud.py` - Application principale (sans Playwright)
- ✅ `requirements_streamlit.txt` - Dépendances adaptées
- ✅ `packages.txt` - Dépendances système
- ✅ `.streamlit/config.toml` - Configuration Streamlit
- ✅ `.streamlit/secrets.toml.template` - Template des secrets

### 2. Modifications apportées pour Streamlit Cloud

- **Navigation web désactivée** : Playwright ne fonctionne pas sur Streamlit Cloud
- **PDF en mémoire** : Utilisation de BytesIO au lieu de fichiers temporaires
- **Gestion des secrets** : Utilisation de `st.secrets` au lieu de `.env`
- **Gestion d'erreurs renforcée** : Pour les outils non disponibles

## 🔧 Étapes de Déploiement

### 1. Préparer votre repository GitHub

```bash
# Créer un nouveau repository ou utiliser l'existant
git add .
git commit -m "Préparation pour déploiement Streamlit Cloud"
git push origin main
```

### 2. Déployer sur Streamlit Cloud

1. Allez sur [share.streamlit.io](https://share.streamlit.io)
2. Connectez votre compte GitHub
3. Sélectionnez votre repository
4. **IMPORTANT**: Définir le fichier principal comme `app_streamlit_cloud.py`
5. Cliquez sur "Deploy"

### 3. Configurer les Secrets

Dans Streamlit Cloud, allez dans **Settings > Secrets** et ajoutez :

```toml
OPENAI_API_KEY = "sk-votre_clé_openai_ici"
SERPER_API_KEY = "votre_clé_serper_ici"
PUSHOVER_TOKEN = "votre_token_pushover_ici"
PUSHOVER_USER = "votre_user_pushover_ici"
```

### 4. Configurer les Requirements

Assurez-vous que Streamlit Cloud utilise `requirements_streamlit.txt` :

- Dans les paramètres avancés, spécifiez le fichier de requirements
- Ou renommez `requirements_streamlit.txt` en `requirements.txt`

## ⚠️ Limitations sur Streamlit Cloud

### Fonctionnalités désactivées :
- **Navigation web avec Playwright** : Trop lourd pour Streamlit Cloud
- **Notifications Pushover avec fichiers** : Pas de système de fichiers persistant

### Fonctionnalités disponibles :
- ✅ **Recherche intelligente** avec GPT-4
- ✅ **Notifications push Pushover** (texte uniquement)
- ✅ **Recherche Google** via Serper API
- ✅ **Recherche Wikipedia**
- ✅ **Génération de PDF** (téléchargement direct)
- ✅ **Exécution Python** pour l'analyse

## 🔍 Test Local

Avant le déploiement, testez localement :

```bash
# Utiliser la version cloud
streamlit run app_streamlit_cloud.py

# Ou utiliser les requirements cloud
pip install -r requirements_streamlit.txt
```

## 🛠️ Dépannage

### Erreur de déploiement :
- Vérifiez que `requirements_streamlit.txt` est utilisé
- Assurez-vous que tous les secrets sont configurés
- Vérifiez les logs de déploiement

### Erreur de secrets :
- Les clés API doivent être dans **Settings > Secrets**
- Format TOML requis (guillemets obligatoires)
- Redémarrez l'app après modification des secrets

### Performance lente :
- C'est normal sur le tier gratuit de Streamlit Cloud
- L'app se met en veille après inactivité

## 🎯 URL de Production

Après déploiement, votre app sera accessible à :
`https://votre-nom-utilisateur-deepsearch-langchain-main.streamlit.app`

## 📱 Utilisation en Production

1. **Recherches simples** : Fonctionnent parfaitement
2. **Recherches complexes** : Peuvent prendre plus de temps
3. **Téléchargement PDF** : Direct depuis l'interface
4. **Partage** : URL publique partageable
