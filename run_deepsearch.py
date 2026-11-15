#!/usr/bin/env python3
"""
Script de lancement pour l'application DeepSearch Streamlit
"""
import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Vérifie que les dépendances sont installées"""
    try:
        import streamlit
        import reportlab
        import langchain
        return True
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("💡 Installez les dépendances avec: pip install -r requirements.txt")
        return False

def _load_local_config() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return
    try:
        import tomllib
    except ImportError:
        return
    with secrets_path.open("rb") as handle:
        secrets = tomllib.load(handle)
    for key in ("GROK_API_KEY", "XAI_API_KEY", "GROK_MODEL"):
        value = secrets.get(key)
        if value and not os.getenv(key):
            os.environ[key] = str(value)


def check_environment():
    """Vérifie les variables d'environnement"""
    _load_local_config()
    if os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"):
        required_vars = []
    else:
        required_vars = ["GROK_API_KEY"]
    optional_vars = ["PUSHOVER_TOKEN", "PUSHOVER_USER", "SERPER_API_KEY"]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ Variables d'environnement manquantes (obligatoires): {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"⚠️  Variables d'environnement manquantes (optionnelles): {', '.join(missing_optional)}")
    
    print("✅ Configuration des variables d'environnement OK")
    return True

def main():
    print("🔍 Démarrage de DeepSearch...")
    
    # Vérifier les dépendances
    if not check_requirements():
        sys.exit(1)
    
    # Vérifier l'environnement
    if not check_environment():
        sys.exit(1)
    
    # Lancer Streamlit
    print("🚀 Lancement de l'interface Streamlit...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py",
            "--server.address", "localhost",
            "--server.port", "8501"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'application")

if __name__ == "__main__":
    main()
