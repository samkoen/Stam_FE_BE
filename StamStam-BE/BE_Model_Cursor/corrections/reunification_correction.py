"""
Méthode de correction : Réunification de 1 rectangle en N lettres.
"""
from typing import List, Tuple, Optional
import numpy as np
import cv2
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew


class ReunificationCorrection(BaseCorrection):
    """
    Correction pour séparer 1 rectangle unifié en N lettres.
    
    Exemple: 1 rectangle détecté comme 'ה' mais devrait être 'ק' + 'י'.
    On re-détecte les rectangles dans ce rectangle pour voir s'il contient 2 lettres.
    """
    
    def __init__(self, image: np.ndarray, weight_file: str, min_contour_area: int = 30):
        """
        Args:
            image: Image OpenCV complète
            weight_file: Chemin vers le fichier de poids du modèle
            min_contour_area: Surface minimale pour la re-détection (plus petit que la détection normale)
        """
        super().__init__(image, weight_file)
        self.min_contour_area = min_contour_area
    
    def _redetect_rectangles_in_rect(self, rect, min_contour_area=30):
        """
        Re-détecte les rectangles dans une région spécifique de l'image.
        (Copie de la fonction depuis letter_detection.py pour éviter les dépendances circulaires)
        """
        x, y, w, h = rect
        
        # Extraire la région de l'image
        x = max(0, int(x))
        y = max(0, int(y))
        w = min(self.image.shape[1] - x, int(w))
        h = min(self.image.shape[0] - y, int(h))
        
        if w <= 0 or h <= 0:
            return []
        
        region = self.image[y:y+h, x:x+w]
        
        if region.size == 0:
            return []
        
        # Détecter les contours dans cette région
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            2
        )
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrage des contours par taille
        valid_rects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_contour_area:
                continue
            
            rx, ry, rw, rh = cv2.boundingRect(contour)
            
            if rw > 5 and rh > 8 and rw < 1000:
                aspect_ratio = rw / rh if rh > 0 else 0
                if 0.1 < aspect_ratio < 5.0:
                    valid_rects.append((rx, ry, rw, rh))
        
        # Trier de droite à gauche (ordre hébreu)
        valid_rects.sort(key=lambda r: r[0] + r[2], reverse=True)
        
        # Convertir en coordonnées absolues
        absolute_rects = []
        for rx, ry, rw, rh in valid_rects:
            abs_x = x + rx
            abs_y = y + ry
            absolute_rects.append((abs_x, abs_y, rw, rh))
        
        return absolute_rects
    
    def try_correct(self, rect_idx: int, valid_rects_final: List[Tuple[int, int, int, int]],
                   valid_codes: List[int], expected_char: str, detected_char: str,
                   reference_text: str = '', detected_text: str = '', 
                   detected_chars: Optional[str] = None) -> CorrectionResult:
        """
        Tente de réunifier 1 rectangle en N lettres.
        
        Vérifie si le rectangle actuel contient en fait plusieurs lettres.
        """
        if rect_idx >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={'reason': 'Invalid rect_idx'})
        
        current_rect = valid_rects_final[rect_idx]
        
        # Re-détecter les rectangles dans le rectangle actuel
        redetected_rects = self._redetect_rectangles_in_rect(current_rect, min_contour_area=self.min_contour_area)
        
        if len(redetected_rects) >= 2:
            # Appliquer la détection des lettres
            redetected_codes = predict_letters(self.image, redetected_rects, self.weight_file)
            
            # Filtrer les codes invalides
            valid_redetected = [(rect, code) for rect, code in zip(redetected_rects, redetected_codes) 
                               if code != 27]
            
            if len(valid_redetected) >= 2:
                detected_chars = [letter_code_to_hebrew(code) for _, code in valid_redetected]
                detected_str = "".join(detected_chars)
                
                # Vérification
                match = False
                if len(expected_char) == 1:
                    # Cas 1 lettre: on vérifie sa présence dans les résultats
                    match = expected_char in detected_chars
                else:
                    # Cas N lettres: on vérifie si la séquence détectée correspond
                    match = expected_char == detected_str
                
                if match:
                    # Succès ! Extraire les rectangles et codes
                    new_rects = [rect for rect, _ in valid_redetected]
                    new_codes = [code for _, code in valid_redetected]
                    
                    return CorrectionResult(
                        success=True,
                        new_rects=new_rects,
                        new_codes=new_codes,
                        num_rects_to_replace=1,
                        metadata={
                            'num_rects_found': len(valid_redetected),
                            'detected_chars': ''.join(detected_chars),
                            'expected_char': expected_char
                        }
                    )
        
        return CorrectionResult(success=False, metadata={'reason': 'Reunification did not find expected letter'})

