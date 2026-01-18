#!/usr/bin/env python3
"""
Script de démarrage Python pour la production.
Alternative au script shell, fonctionne sur Windows et Linux.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_prerequisites():
    """Vérifie les prérequis avant de démarrer."""
    errors = []
    warnings = []
    
    # Vérifier l'environnement
    env = os.getenv('STAMSTAM_ENV', 'dev')
    if env not in ('prod', 'production', 'pro'):
        warnings.append(f"STAMSTAM_ENV={env} - recommandé 'prod' en production")
    
    # Vérifier le modèle ML
    model_path = os.getenv('STAMSTAM_MODEL_PATH')
    if not model_path or not os.path.exists(model_path):
        default_path = Path(__file__).parent / 'ocr' / 'model' / 'output' / 'Nadam_beta_1_256_30.hdf5'
        if model_path:
            errors.append(f"Le fichier de modèle n'existe pas: {model_path}")
        else:
            errors.append(f"STAMSTAM_MODEL_PATH non défini et fichier par défaut absent: {default_path}")
    
    # Vérifier le dossier overflow
    overflow_dir = os.getenv('STAMSTAM_OVERFLOW_DIR')
    if not overflow_dir or not os.path.exists(overflow_dir):
        default_dir = Path(__file__).parent / 'overflow'
        if overflow_dir:
            errors.append(f"Le dossier overflow n'existe pas: {overflow_dir}")
        else:
            errors.append(f"STAMSTAM_OVERFLOW_DIR non défini et dossier par défaut absent: {default_dir}")
    
    # Vérifier Gunicorn
    try:
        import gunicorn
    except ImportError:
        errors.append("Gunicorn n'est pas installé. Installez-le avec: pip install gunicorn")
    
    return errors, warnings

def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("Démarrage de StamStam API en production")
    print("=" * 60)
    
    # Vérifier les prérequis
    errors, warnings = check_prerequisites()
    
    if warnings:
        print("\n⚠️  Avertissements:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if errors:
        print("\n❌ Erreurs:")
        for error in errors:
            print(f"  - {error}")
        print("\nCorrigez les erreurs avant de continuer.")
        sys.exit(1)
    
    # Charger .env si disponible
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print(f"\n📄 Chargement des variables depuis {env_file}")
        # Note: En production, utilisez python-dotenv ou configurez les variables d'environnement autrement
    
    # Afficher la configuration
    print("\nConfiguration:")
    print(f"  Environment: {os.getenv('STAMSTAM_ENV', 'dev')}")
    print(f"  Host: {os.getenv('STAMSTAM_HOST', '0.0.0.0')}")
    print(f"  Port: {os.getenv('STAMSTAM_PORT', '8000')}")
    print(f"  Model: {os.getenv('STAMSTAM_MODEL_PATH', 'par défaut')}")
    print(f"  Overflow: {os.getenv('STAMSTAM_OVERFLOW_DIR', 'par défaut')}")
    
    # Démarrer Gunicorn
    print("\n🚀 Démarrage de Gunicorn...")
    print("=" * 60)
    
    # Commande Gunicorn
    gunicorn_cmd = [
        'gunicorn',
        '--config', 'gunicorn_config.py',
        'app:app'
    ]
    
    try:
        # Exécuter Gunicorn (remplace le processus actuel)
        os.execvp('gunicorn', gunicorn_cmd)
    except FileNotFoundError:
        print("❌ Erreur: Gunicorn n'est pas trouvé dans le PATH")
        print("   Installez-le avec: pip install gunicorn")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

