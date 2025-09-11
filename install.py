#!/usr/bin/env python3
"""
Script d'installation pour DeepSearch
"""
import subprocess
import sys
import os

def install_requirements():
    """Installe les dépendances Python"""
    print("📦 Installation des dépendances Python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dépendances Python installées avec succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation des dépendances: {e}")
        return False

def install_playwright():
    """Installe les navigateurs Playwright"""
    print("🎭 Installation des navigateurs Playwright...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        print("✅ Navigateurs Playwright installés avec succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation de Playwright: {e}")
        return False

def check_env_file():
    """Vérifie si le fichier .env existe"""
    if not os.path.exists('.env'):
        print("⚠️  Fichier .env non trouvé")
        print("💡 Copiez config_example.env vers .env et configurez vos clés API")
        return False
    else:
        print("✅ Fichier .env trouvé")
        return True

def main():
    print("🔍 Installation de DeepSearch...")
    print("=" * 50)
    
    success = True
    
    # Installer les dépendances Python
    if not install_requirements():
        success = False
    
    # Installer Playwright
    if not install_playwright():
        success = False
    
    # Vérifier le fichier .env
    check_env_file()
    
    print("=" * 50)
    if success:
        print("🎉 Installation terminée avec succès!")
        print("🚀 Vous pouvez maintenant lancer l'application avec: python run_deepsearch.py")
    else:
        print("❌ L'installation a échoué. Vérifiez les erreurs ci-dessus.")
        sys.exit(1)

if __name__ == "__main__":
    main()
