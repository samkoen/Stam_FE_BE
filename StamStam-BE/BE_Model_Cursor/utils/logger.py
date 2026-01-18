"""
Module de logging centralisé pour l'application StamStam.
Fournit une configuration de logging structurée avec différents niveaux.
"""
import logging
import sys
import os
from typing import Optional


class StamStamLogger:
    """
    Logger personnalisé pour StamStam avec formatage structuré.
    """
    
    # Format de log par défaut
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Format détaillé pour le debug
    DEBUG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    @staticmethod
    def setup_logger(
        name: str = 'stamstam',
        level: Optional[str] = None,
        debug: bool = False,
        log_file: Optional[str] = None
    ) -> logging.Logger:
        """
        Configure et retourne un logger pour l'application.
        
        Args:
            name: Nom du logger (par défaut 'stamstam')
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR). Si None, utilise debug pour déterminer.
            debug: Si True, active le mode DEBUG avec format détaillé
            log_file: Chemin vers un fichier de log (optionnel). Si None, logs uniquement dans stdout.
            
        Returns:
            logging.Logger: Logger configuré
        """
        logger = logging.getLogger(name)
        
        # Éviter de reconfigurer un logger déjà configuré
        if logger.handlers:
            return logger
        
        # Déterminer le niveau de log
        if level is None:
            log_level = logging.DEBUG if debug else logging.INFO
        else:
            log_level = getattr(logging, level.upper(), logging.INFO)
        
        logger.setLevel(log_level)
        
        # Format selon le mode debug
        formatter = logging.Formatter(
            StamStamLogger.DEBUG_FORMAT if debug else StamStamLogger.LOG_FORMAT,
            datefmt=StamStamLogger.DATE_FORMAT
        )
        
        # Handler pour stdout (toujours présent)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler pour fichier (optionnel)
        if log_file:
            try:
                # Créer le répertoire si nécessaire
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                # Vérifier les permissions d'écriture
                # Essayer de créer/ouvrir le fichier en mode append pour vérifier les permissions
                test_file = open(log_file, 'a', encoding='utf-8')
                test_file.close()
                
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                
            except (OSError, PermissionError) as e:
                # Si on ne peut pas écrire dans le fichier, continuer avec la console uniquement
                # Logger un avertissement dans la console
                import warnings
                warnings.warn(
                    f"Impossible d'écrire dans le fichier de log '{log_file}': {e}. "
                    f"Les logs seront uniquement affichés dans la console.",
                    UserWarning
                )
                # Logger aussi via le logger si possible (mais sans handler fichier)
                logger.warning(
                    f"Fichier de log '{log_file}' inaccessible: {e}. "
                    f"Logs uniquement dans la console."
                )
        
        return logger
    
    @staticmethod
    def get_logger(name: str = 'stamstam', debug: bool = False) -> logging.Logger:
        """
        Récupère ou crée un logger avec la configuration par défaut.
        
        Args:
            name: Nom du logger
            debug: Si True, active le mode DEBUG
            
        Returns:
            logging.Logger: Logger configuré
        """
        logger = logging.getLogger(name)
        
        # Si le logger n'a pas de handlers, le configurer
        if not logger.handlers:
            # Vérifier les variables d'environnement
            env_debug = os.getenv('STAMSTAM_DEBUG', '').lower() in ('true', '1', 'yes')
            env_log_file = os.getenv('STAMSTAM_LOG_FILE', '').strip()
            
            # Détecter l'environnement (production vs développement)
            # En production, on désactive le fichier de log par défaut pour éviter les problèmes
            is_production = os.getenv('STAMSTAM_ENV', '').lower() in ('prod', 'production', 'pro')
            
            # Si aucun fichier de log n'est spécifié explicitement
            if not env_log_file:
                if is_production:
                    # En production, pas de fichier de log par défaut (utiliser uniquement stdout)
                    # Les logs seront gérés par le système (systemd, docker, etc.)
                    env_log_file = None
                else:
                    # En développement, créer un fichier de log local
                    try:
                        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        logs_dir = os.path.join(backend_dir, 'logs')
                        if not os.path.exists(logs_dir):
                            os.makedirs(logs_dir, exist_ok=True)
                        # Fichier de log par défaut : logs/stamstam.log
                        env_log_file = os.path.join(logs_dir, 'stamstam.log')
                    except (OSError, PermissionError):
                        # Si on ne peut pas créer le dossier, pas de fichier de log
                        env_log_file = None
            elif env_log_file.lower() == 'none' or env_log_file.lower() == 'false':
                # Permettre de désactiver explicitement le fichier de log
                env_log_file = None
            
            debug_mode = debug or env_debug
            
            StamStamLogger.setup_logger(
                name=name,
                debug=debug_mode,
                log_file=env_log_file
            )
        
        return logger


# Fonction utilitaire pour faciliter l'utilisation
def get_logger(name: str = None, debug: bool = False) -> logging.Logger:
    """
    Fonction utilitaire pour obtenir un logger.
    
    Args:
        name: Nom du logger (par défaut, utilise le nom du module appelant)
        debug: Si True, active le mode DEBUG
        
    Returns:
        logging.Logger: Logger configuré
    """
    if name is None:
        # Utiliser le nom du module appelant
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'stamstam')
    
    return StamStamLogger.get_logger(name, debug=debug)

