"""
Configuration centralisée pour l'application StamStam.
Toutes les configurations sont chargées depuis les variables d'environnement
avec des valeurs par défaut pour le développement.
"""
import os
from pathlib import Path
from typing import List


class Config:
    """
    Classe de configuration centralisée.
    Toutes les valeurs sont chargées depuis les variables d'environnement.
    """
    
    # ==================== Chemins de base ====================
    # Répertoire de base du projet (où se trouve ce fichier config.py)
    BASE_DIR = Path(__file__).parent.absolute()
    
    # ==================== Environnement ====================
    ENV = os.getenv('STAMSTAM_ENV', 'dev').lower()
    DEBUG = os.getenv('STAMSTAM_DEBUG', '').lower() in ('true', '1', 'yes')
    IS_PRODUCTION = ENV in ('prod', 'production', 'pro')
    
    # ==================== Chemins des fichiers ====================
    # Chemin vers le fichier de poids du modèle ML
    MODEL_PATH = os.getenv(
        'STAMSTAM_MODEL_PATH',
        str(BASE_DIR / 'ocr' / 'model' / 'output' / 'Nadam_beta_1_256_30.hdf5')
    )
    
    # Chemin vers le dossier overflow/ contenant les fichiers texte des parachot
    OVERFLOW_DIR = os.getenv(
        'STAMSTAM_OVERFLOW_DIR',
        str(BASE_DIR / 'overflow')
    )
    
    # ==================== Configuration du serveur ====================
    # Host et port pour le serveur FastAPI
    HOST = os.getenv('STAMSTAM_HOST', '0.0.0.0')
    PORT = int(os.getenv('STAMSTAM_PORT', '8000'))
    
    # ==================== Configuration CORS ====================
    # Origines autorisées pour CORS
    # En production, NE PAS utiliser "*" - spécifier les domaines autorisés
    CORS_ORIGINS_STR = os.getenv('STAMSTAM_CORS_ORIGINS', '')
    if CORS_ORIGINS_STR:
        # Si défini, splitter par virgule
        CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(',')]
    elif IS_PRODUCTION:
        # En production, par défaut aucune origine (doit être configuré explicitement)
        CORS_ORIGINS = []
    else:
        # En développement, autoriser toutes les origines
        CORS_ORIGINS = ["*"]
    
    # ==================== Configuration Logging ====================
    # Fichier de log (None = uniquement stdout)
    LOG_FILE = os.getenv('STAMSTAM_LOG_FILE', None)
    if LOG_FILE and LOG_FILE.lower() in ('none', 'false', ''):
        LOG_FILE = None
    
    # Niveau de log (DEBUG, INFO, WARNING, ERROR)
    LOG_LEVEL = os.getenv('STAMSTAM_LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')
    
    # ==================== Configuration API ====================
    # Taille maximale des fichiers uploadés (en MB)
    MAX_UPLOAD_SIZE_MB = int(os.getenv('STAMSTAM_MAX_UPLOAD_SIZE_MB', '10'))
    MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # Formats de fichiers acceptés
    ACCEPTED_IMAGE_FORMATS = ['image/jpeg', 'image/jpg', 'image/png']
    
    # ==================== Validation ====================
    @classmethod
    def validate(cls):
        """
        Valide la configuration et affiche des avertissements si nécessaire.
        """
        warnings = []
        
        # Vérifier que le fichier de modèle existe
        if not os.path.exists(cls.MODEL_PATH):
            warnings.append(f"⚠️  Le fichier de modèle n'existe pas : {cls.MODEL_PATH}")
        
        # Vérifier que le dossier overflow existe
        if not os.path.exists(cls.OVERFLOW_DIR):
            warnings.append(f"⚠️  Le dossier overflow n'existe pas : {cls.OVERFLOW_DIR}")
        
        # Avertissement en production
        if cls.IS_PRODUCTION:
            if cls.CORS_ORIGINS == ["*"]:
                warnings.append("⚠️  CORS autorise toutes les origines (*) en production - c'est risqué pour la sécurité")
            
            if cls.DEBUG:
                warnings.append("⚠️  DEBUG=True en production - désactivez-le pour la sécurité")
            
            if not cls.CORS_ORIGINS:
                warnings.append("⚠️  Aucune origine CORS configurée en production - l'API ne sera pas accessible")
        
        return warnings
    
    @classmethod
    def print_config(cls):
        """
        Affiche la configuration actuelle (sans les valeurs sensibles).
        """
        print("=" * 60)
        print("Configuration StamStam")
        print("=" * 60)
        print(f"Environnement: {cls.ENV} ({'Production' if cls.IS_PRODUCTION else 'Développement'})")
        print(f"DEBUG: {cls.DEBUG}")
        print(f"MODEL_PATH: {cls.MODEL_PATH}")
        print(f"OVERFLOW_DIR: {cls.OVERFLOW_DIR}")
        print(f"Host: {cls.HOST}")
        print(f"Port: {cls.PORT}")
        print(f"CORS Origins: {cls.CORS_ORIGINS}")
        print(f"LOG_FILE: {cls.LOG_FILE or 'stdout uniquement'}")
        print(f"LOG_LEVEL: {cls.LOG_LEVEL}")
        print(f"MAX_UPLOAD_SIZE: {cls.MAX_UPLOAD_SIZE_MB} MB")
        print("=" * 60)


# Instance globale de configuration
config = Config()


# Valider la configuration au chargement (seulement si __main__ ou si explicitement demandé)
if __name__ == '__main__':
    config.print_config()
    warnings = config.validate()
    if warnings:
        print("\n⚠️  Avertissements:")
        for warning in warnings:
            print(f"  {warning}")

