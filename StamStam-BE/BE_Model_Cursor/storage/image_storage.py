"""
Module de stockage des images utilisateur.

Ce module fournit une abstraction pour le stockage des images, permettant de :
- Stocker les images originales et les résultats par utilisateur
- Faciliter le passage à une base de données plus tard

Pour l'instant, utilise un système de fichiers (un dossier par utilisateur).
Plus tard, on pourra remplacer par une base de données sans changer l'interface.
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
from BE_Model_Cursor.utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_email(email: str) -> str:
    """
    Nettoie un email pour l'utiliser comme nom de dossier.
    Remplace les caractères non autorisés par des underscores.
    
    Args:
        email: Email de l'utilisateur
        
    Returns:
        str: Email nettoyé pour usage comme nom de dossier
    """
    # Remplacer les caractères non autorisés par des underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', email)
    return sanitized


def get_user_storage_path(base_dir: str, email: str) -> Path:
    """
    Retourne le chemin du dossier de stockage pour un utilisateur.
    
    Args:
        base_dir: Dossier de base pour le stockage des utilisateurs
        email: Email de l'utilisateur
        
    Returns:
        Path: Chemin vers le dossier de l'utilisateur
    """
    sanitized_email = sanitize_email(email)
    user_dir = Path(base_dir) / sanitized_email
    return user_dir


def ensure_user_directory(base_dir: str, email: str) -> Path:
    """
    Crée le dossier de l'utilisateur s'il n'existe pas.
    
    Args:
        base_dir: Dossier de base pour le stockage des utilisateurs
        email: Email de l'utilisateur
        
    Returns:
        Path: Chemin vers le dossier de l'utilisateur (créé si nécessaire)
    """
    user_dir = get_user_storage_path(base_dir, email)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Créer les sous-dossiers
    (user_dir / "originals").mkdir(exist_ok=True)
    (user_dir / "results").mkdir(exist_ok=True)
    
    return user_dir


def sanitize_paracha_name(paracha_name: Optional[str]) -> str:
    """
    Nettoie le nom de la paracha pour l'utiliser dans un nom de fichier.
    
    Args:
        paracha_name: Nom de la paracha
        
    Returns:
        str: Nom de paracha nettoyé (ou "unknown" si None)
    """
    if not paracha_name or paracha_name in ("Non détectée", "Aucune lettre détectée", "Aucune lettre valide détectée"):
        return "unknown"
    
    # Remplacer les caractères non autorisés par des underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', paracha_name)
    # Limiter la longueur
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized


def generate_filename(
    original_filename: Optional[str] = None, 
    prefix: str = "image",
    paracha_name: Optional[str] = None
) -> str:
    """
    Génère un nom de fichier unique basé sur la date/heure et le nom de la paracha.
    
    Args:
        original_filename: Nom de fichier original (optionnel, pour préserver l'extension)
        prefix: Préfixe pour le nom de fichier
        paracha_name: Nom de la paracha détectée (optionnel)
        
    Returns:
        str: Nom de fichier unique
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    if original_filename:
        # Extraire l'extension du fichier original
        ext = Path(original_filename).suffix
        if not ext:
            ext = ".jpg"  # Par défaut
    else:
        ext = ".jpg"
    
    # Ajouter le nom de la paracha si fourni
    paracha_part = ""
    if paracha_name:
        sanitized_paracha = sanitize_paracha_name(paracha_name)
        paracha_part = f"_{sanitized_paracha}"
    
    return f"{prefix}{paracha_part}_{timestamp}{ext}"


class ImageStorage:
    """
    Classe pour gérer le stockage des images utilisateur.
    
    Cette classe fournit une abstraction qui peut être facilement remplacée
    par une implémentation basée sur une base de données plus tard.
    """
    
    def __init__(self, base_storage_dir: str):
        """
        Initialise le stockage d'images.
        
        Args:
            base_storage_dir: Dossier de base pour le stockage des utilisateurs
        """
        self.base_dir = Path(base_storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ImageStorage initialisé avec base_dir: {self.base_dir}")
    
    def save_original_image(
        self, 
        email: str, 
        image: np.ndarray, 
        original_filename: Optional[str] = None,
        paracha_name: Optional[str] = None
    ) -> str:
        """
        Sauvegarde l'image originale de l'utilisateur.
        
        Args:
            email: Email de l'utilisateur
            image: Image OpenCV (numpy array)
            original_filename: Nom de fichier original (optionnel)
            paracha_name: Nom de la paracha détectée (optionnel)
            
        Returns:
            str: Chemin relatif du fichier sauvegardé (pour faciliter le passage à une DB)
        """
        user_dir = ensure_user_directory(str(self.base_dir), email)
        filename = generate_filename(original_filename, prefix="original", paracha_name=paracha_name)
        filepath = user_dir / "originals" / filename
        
        cv2.imwrite(str(filepath), image)
        logger.info(f"Image originale sauvegardée pour {email}: {filepath}")
        
        # Retourner un chemin relatif pour faciliter le passage à une DB
        return f"{sanitize_email(email)}/originals/{filename}"
    
    def save_result_image(
        self, 
        email: str, 
        image: np.ndarray, 
        original_filename: Optional[str] = None,
        paracha_name: Optional[str] = None
    ) -> str:
        """
        Sauvegarde l'image de résultat (avec les rectangles colorés).
        
        Args:
            email: Email de l'utilisateur
            image: Image OpenCV (numpy array)
            original_filename: Nom de fichier original (optionnel, pour référence)
            paracha_name: Nom de la paracha détectée (optionnel)
            
        Returns:
            str: Chemin relatif du fichier sauvegardé (pour faciliter le passage à une DB)
        """
        user_dir = ensure_user_directory(str(self.base_dir), email)
        filename = generate_filename(original_filename, prefix="result", paracha_name=paracha_name)
        filepath = user_dir / "results" / filename
        
        cv2.imwrite(str(filepath), image)
        logger.info(f"Image résultat sauvegardée pour {email}: {filepath}")
        
        # Retourner un chemin relatif pour faciliter le passage à une DB
        return f"{sanitize_email(email)}/results/{filename}"
    
    def save_image_pair(
        self, 
        email: str, 
        original_image: np.ndarray, 
        result_image: np.ndarray,
        original_filename: Optional[str] = None,
        paracha_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Sauvegarde à la fois l'image originale et l'image de résultat.
        
        Args:
            email: Email de l'utilisateur
            original_image: Image originale OpenCV (numpy array)
            result_image: Image de résultat OpenCV (numpy array)
            original_filename: Nom de fichier original (optionnel)
            paracha_name: Nom de la paracha détectée (optionnel)
            
        Returns:
            Tuple[str, str]: (chemin_relatif_original, chemin_relatif_resultat)
        """
        original_path = self.save_original_image(email, original_image, original_filename, paracha_name)
        result_path = self.save_result_image(email, result_image, original_filename, paracha_name)
        
        return (original_path, result_path)
    
    def get_user_images(self, email: str) -> dict:
        """
        Récupère la liste des images d'un utilisateur.
        
        Args:
            email: Email de l'utilisateur
            
        Returns:
            dict: {
                'originals': [liste des chemins],
                'results': [liste des chemins]
            }
        """
        user_dir = get_user_storage_path(str(self.base_dir), email)
        
        originals = []
        results = []
        
        if user_dir.exists():
            originals_dir = user_dir / "originals"
            results_dir = user_dir / "results"
            
            if originals_dir.exists():
                originals = [str(f.name) for f in originals_dir.iterdir() if f.is_file()]
            
            if results_dir.exists():
                results = [str(f.name) for f in results_dir.iterdir() if f.is_file()]
        
        return {
            'originals': sorted(originals),
            'results': sorted(results)
        }

