"""
Classe abstraite de base pour les méthodes de correction des erreurs de détection.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np


class CorrectionResult:
    """
    Résultat d'une tentative de correction.
    """
    def __init__(self, success: bool, new_rects: Optional[List[Tuple[int, int, int, int]]] = None,
                 new_codes: Optional[List[int]] = None, num_rects_to_replace: int = 1,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Args:
            success: True si la correction a réussi
            new_rects: Liste des nouveaux rectangles (si success=True)
            new_codes: Liste des nouveaux codes de lettres (si success=True)
            num_rects_to_replace: Nombre de rectangles à remplacer (par défaut 1)
            metadata: Métadonnées supplémentaires (logs, etc.)
        """
        self.success = success
        self.new_rects = new_rects or []
        self.new_codes = new_codes or []
        self.num_rects_to_replace = num_rects_to_replace
        self.metadata = metadata or {}


class BaseCorrection(ABC):
    """
    Classe abstraite de base pour toutes les méthodes de correction.
    
    Chaque sous-classe implémente une méthode spécifique de correction :
    - Extension de hauteur pour ה→ק
    - Fusion de N rectangles en 1
    - Réunification de 1 rectangle en N
    - etc.
    """
    
    def __init__(self, image: np.ndarray, weight_file: str):
        """
        Args:
            image: Image OpenCV complète (numpy array) en couleur BGR
            weight_file: Chemin vers le fichier de poids du modèle ML
        """
        self.image = image
        self.weight_file = weight_file
    
    @abstractmethod
    def try_correct(self, rect_idx: int, valid_rects_final: List[Tuple[int, int, int, int]],
                   valid_codes: List[int], expected_char: str, detected_char: str,
                   reference_text: str = '', detected_text: str = '', 
                   detected_chars: Optional[str] = None) -> CorrectionResult:
        """
        Tente de corriger une erreur de détection.
        
        Args:
            rect_idx: Index du rectangle à corriger dans valid_rects_final
            valid_rects_final: Liste des rectangles actuels
            valid_codes: Liste des codes de lettres actuels
            expected_char: Lettre attendue (dans le texte de référence)
            detected_char: Lettre détectée (actuellement, pour 1 rectangle)
            reference_text: Texte de référence complet
            detected_text: Texte détecté actuel
            detected_chars: Chaîne de caractères détectés (pour N rectangles, ex: "צלי")
        
        Returns:
            CorrectionResult: Résultat de la tentative de correction
        """
        pass
    
    def get_name(self) -> str:
        """
        Retourne le nom de la méthode de correction (pour les logs).
        """
        return self.__class__.__name__

