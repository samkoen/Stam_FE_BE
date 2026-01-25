"""
Méthode de correction : Recherche de lettre manquante par réunification.
"""
from typing import List, Tuple, Optional
import numpy as np
import cv2
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.utils.contour_detector import _in_same_line
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine


class MissingLetterCorrection(BaseCorrection):
    """
    Correction pour trouver une lettre manquante en réunifiant des rectangles.
    
    Si une lettre est manquante, on essaie de re-détecter les rectangles dans le rectangle
    précédent ou suivant pour voir s'ils contiennent plusieurs lettres (dont la lettre manquante).
    """
    
    def __init__(self, image: np.ndarray, weight_file: str, min_contour_area: int = 30):
        """
        Args:
            image: Image OpenCV complète
            weight_file: Chemin vers le fichier de poids du modèle
            min_contour_area: Surface minimale pour la re-détection
        """
        super().__init__(image, weight_file)
        self.min_contour_area = min_contour_area
    
    def _redetect_rectangles_in_rect(self, rect):
        """
        Re-détecte les rectangles dans une région spécifique de l'image.
        (Copie de la fonction depuis letter_detection.py)
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
            if area < self.min_contour_area:
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
                   valid_codes: List[int], expected_char: str, detected_char: str = '',
                   reference_text: str = '', detected_text: str = '', 
                   detected_chars: Optional[str] = None) -> CorrectionResult:
        """
        Tente de trouver la lettre manquante en réunifiant des rectangles.
        
        Essaie d'abord le rectangle précédent, puis le rectangle suivant.
        IMPORTANT: Ne réunifie que si les rectangles sont sur la même ligne.
        """
        if rect_idx == 0 and rect_idx >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={'reason': 'Invalid rect_idx'})
        
        # Essayer d'abord le rectangle précédent (si disponible et sur la même ligne)
        if rect_idx > 0:
            prev_rect = valid_rects_final[rect_idx - 1]
            
            # Vérifier si le rectangle précédent est sur la même ligne
            # Pour une lettre manquante, on compare avec le rectangle suivant (rect_idx) s'il existe
            can_try_prev = True
            if rect_idx < len(valid_rects_final):
                current_rect = valid_rects_final[rect_idx]
                # Vérifier si prev_rect et current_rect sont sur la même ligne
                # Utiliser line_number si disponible, sinon _in_same_line pour compatibilité
                if isinstance(prev_rect, RectangleWithLine) and isinstance(current_rect, RectangleWithLine):
                    if prev_rect.line_number != current_rect.line_number:
                        print(f"  → Rectangle précédent (index {rect_idx - 1}, line {prev_rect.line_number}) n'est PAS sur la même ligne que rectangle suivant (line {current_rect.line_number}) → Ignoré")
                        can_try_prev = False
                else:
                    # Compatibilité avec les tuples
                    if len(valid_rects_final) > 0:
                        width_mean = sum(r[2] if not isinstance(r, RectangleWithLine) else r.w for r in valid_rects_final) / len(valid_rects_final)
                    else:
                        width_mean = 50
                    if not _in_same_line(prev_rect, current_rect, width_mean):
                        print(f"  → Rectangle précédent (index {rect_idx - 1}) n'est PAS sur la même ligne → Ignoré")
                        can_try_prev = False
            
            if can_try_prev:
                print(f"  → Étape 1: Analyse du rectangle précédent (index {rect_idx - 1})")
                
                redetected_rects = self._redetect_rectangles_in_rect(prev_rect)
                print(f"  → Résultat de la re-détection: {len(redetected_rects)} rectangle(s) trouvé(s)")
                
                if len(redetected_rects) >= 2:
                    # Appliquer la détection des lettres
                    redetected_codes = predict_letters(self.image, redetected_rects, self.weight_file)
                    
                    # Filtrer les codes invalides
                    valid_redetected = [(rect, code) for rect, code in zip(redetected_rects, redetected_codes) 
                                       if code != 27]
                    
                    if len(valid_redetected) >= 2:
                        detected_chars = [letter_code_to_hebrew(code) for _, code in valid_redetected]
                        print(f"  → Résultat: Lettres détectées = '{''.join(detected_chars)}'")
                        print(f"  → Vérification: La lettre manquante '{expected_char}' est-elle présente?")
                        
                        if expected_char in detected_chars:
                            print(f"  → ✓ OUI! La lettre '{expected_char}' a été trouvée!")
                            print(f"  → ✓ RÉUNIFICATION RÉUSSIE: Je garde le résultat (1 rectangle → {len(valid_redetected)} rectangles)")
                            
                            # Extraire les rectangles et codes
                            new_rects = [rect for rect, _ in valid_redetected]
                            new_codes = [code for _, code in valid_redetected]
                            
                            return CorrectionResult(
                                success=True,
                                new_rects=new_rects,
                                new_codes=new_codes,
                                num_rects_to_replace=1,  # On remplace le rectangle précédent
                                metadata={
                                    'rect_to_replace_idx': rect_idx - 1,  # Index du rectangle à remplacer (précédent)
                                    'num_rects_found': len(valid_redetected),
                                    'detected_chars': ''.join(detected_chars),
                                    'expected_char': expected_char
                                }
                            )
                        else:
                            print(f"  → ✗ NON! La lettre '{expected_char}' n'a PAS été trouvée dans '{''.join(detected_chars)}'")
        
        # Si le rectangle précédent n'a pas fonctionné, essayer le rectangle suivant (si sur la même ligne)
        if rect_idx < len(valid_rects_final):
            next_rect = valid_rects_final[rect_idx]
            
            # Vérifier si le rectangle suivant est sur la même ligne
            # Comparer avec le rectangle précédent (rect_idx - 1) s'il existe
            can_try_next = True
            if rect_idx > 0:
                prev_rect = valid_rects_final[rect_idx - 1]
                # Vérifier si prev_rect et next_rect sont sur la même ligne
                # Utiliser line_number si disponible, sinon _in_same_line pour compatibilité
                if isinstance(prev_rect, RectangleWithLine) and isinstance(next_rect, RectangleWithLine):
                    if prev_rect.line_number != next_rect.line_number:
                        print(f"  → Rectangle suivant (index {rect_idx}, line {next_rect.line_number}) n'est PAS sur la même ligne que rectangle précédent (line {prev_rect.line_number}) → Ignoré")
                        can_try_next = False
                else:
                    # Compatibilité avec les tuples
                    if len(valid_rects_final) > 0:
                        width_mean = sum(r[2] if not isinstance(r, RectangleWithLine) else r.w for r in valid_rects_final) / len(valid_rects_final)
                    else:
                        width_mean = 50
                    if not _in_same_line(prev_rect, next_rect, width_mean):
                        print(f"  → Rectangle suivant (index {rect_idx}) n'est PAS sur la même ligne → Ignoré")
                        can_try_next = False
            
            if can_try_next:
                print(f"  → Étape 2: Essai avec le rectangle suivant (index {rect_idx})")
                
                redetected_rects = self._redetect_rectangles_in_rect(next_rect)
                print(f"  → Résultat de la re-détection: {len(redetected_rects)} rectangle(s) trouvé(s)")
                
                if len(redetected_rects) >= 2:
                    # Appliquer la détection des lettres
                    redetected_codes = predict_letters(self.image, redetected_rects, self.weight_file)
                    
                    # Filtrer les codes invalides
                    valid_redetected = [(rect, code) for rect, code in zip(redetected_rects, redetected_codes) 
                                       if code != 27]
                    
                    if len(valid_redetected) >= 2:
                        detected_chars = [letter_code_to_hebrew(code) for _, code in valid_redetected]
                        print(f"  → Résultat: Lettres détectées = '{''.join(detected_chars)}'")
                        print(f"  → Vérification: La lettre manquante '{expected_char}' est-elle présente?")
                        
                        if expected_char in detected_chars:
                            print(f"  → ✓ OUI! La lettre '{expected_char}' a été trouvée!")
                            print(f"  → ✓ RÉUNIFICATION RÉUSSIE: Je garde le résultat (1 rectangle → {len(valid_redetected)} rectangles)")
                            
                            # Extraire les rectangles et codes
                            new_rects = [rect for rect, _ in valid_redetected]
                            new_codes = [code for _, code in valid_redetected]
                            
                            return CorrectionResult(
                                success=True,
                                new_rects=new_rects,
                                new_codes=new_codes,
                                num_rects_to_replace=1,  # On remplace le rectangle suivant
                                metadata={
                                    'rect_to_replace_idx': rect_idx,  # Index du rectangle à remplacer (suivant)
                                    'num_rects_found': len(valid_redetected),
                                    'detected_chars': ''.join(detected_chars),
                                    'expected_char': expected_char
                                }
                            )
                        else:
                            print(f"  → ✗ NON! La lettre '{expected_char}' n'a PAS été trouvée dans '{''.join(detected_chars)}'")
        
        return CorrectionResult(success=False, metadata={'reason': 'Letter not found in re-detected rectangles'})

