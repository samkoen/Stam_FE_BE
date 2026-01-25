"""
Méthode de correction : Fusion de N rectangles en 1 lettre.
"""
from typing import List, Tuple
import numpy as np
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.utils.contour_detector import union_rect, _in_same_line
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine


class FusionCorrection(BaseCorrection):
    """
    Correction pour fusionner N rectangles détectés en 1 lettre attendue.
    
    Exemple: צ+י détectés au lieu de ז attendu, ou צ+ל+י au lieu de ז.
    """
    
    def try_correct(self, rect_idx: int, valid_rects_final: List[Tuple[int, int, int, int]],
                   valid_codes: List[int], expected_char: str, detected_char: str,
                   reference_text: str, detected_text: str, detected_chars: str = None) -> CorrectionResult:
        """
        Tente de fusionner N rectangles en 1 lettre.
        
        Args:
            detected_chars: Chaîne de caractères détectés (ex: "צלי" pour 3 rectangles)
                            Si None, utilise detected_char (1 rectangle)
        """
        # Utiliser detected_chars si fourni, sinon detected_char
        chars_to_use = detected_chars if detected_chars else detected_char
        num_rects = len(chars_to_use)
        
        # Vérifier qu'on a assez de rectangles
        if rect_idx + num_rects - 1 >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={'reason': 'Not enough rectangles'})
        
        # Vérifier que tous les rectangles à fusionner sont sur la même ligne
        # Utiliser line_number si disponible, sinon utiliser _in_same_line pour compatibilité
        for j in range(num_rects - 1):
            rect_i = valid_rects_final[rect_idx + j]
            rect_j = valid_rects_final[rect_idx + j + 1]
            
            # Si les deux rectangles sont des RectangleWithLine, utiliser line_number
            if isinstance(rect_i, RectangleWithLine) and isinstance(rect_j, RectangleWithLine):
                if rect_i.line_number != rect_j.line_number:
                    return CorrectionResult(
                        success=False, 
                        metadata={'reason': f'Rectangles {rect_idx + j} (line {rect_i.line_number}) and {rect_idx + j + 1} (line {rect_j.line_number}) not on same line'}
                    )
            else:
                # Compatibilité avec les tuples : utiliser _in_same_line
                if len(valid_rects_final) > 0:
                    width_mean = sum(r[2] if not isinstance(r, RectangleWithLine) else r.w for r in valid_rects_final) / len(valid_rects_final)
                else:
                    width_mean = 50
                if not _in_same_line(rect_i, rect_j, width_mean):
                    return CorrectionResult(
                        success=False, 
                        metadata={'reason': f'Rectangles {rect_idx + j} and {rect_idx + j + 1} not on same line'}
                    )
        
        # Tous les rectangles sont sur la même ligne → on peut fusionner
        # Fusionner tous les rectangles (N rectangles en 1)
        # Commencer avec le premier rectangle
        first_rect = valid_rects_final[rect_idx]
        # Extraire (x, y, w, h) si RectangleWithLine
        if isinstance(first_rect, RectangleWithLine):
            fused_rect = (first_rect.x, first_rect.y, first_rect.w, first_rect.h)
            line_number = first_rect.line_number  # Conserver le numéro de ligne
        else:
            fused_rect = first_rect
            line_number = None  # Pas de numéro de ligne disponible
        
        for j in range(1, num_rects):
            rect_j = valid_rects_final[rect_idx + j]
            # Extraire (x, y, w, h) si RectangleWithLine
            if isinstance(rect_j, RectangleWithLine):
                rect_j_tuple = (rect_j.x, rect_j.y, rect_j.w, rect_j.h)
            else:
                rect_j_tuple = rect_j
            fused_rect = union_rect(fused_rect, rect_j_tuple)
        
        # Prédire la lettre sur le rectangle fusionné
        fused_rects = [fused_rect]
        fused_codes = predict_letters(self.image, fused_rects, self.weight_file)
        
        if len(fused_codes) > 0 and fused_codes[0] != 27:
            fused_char = letter_code_to_hebrew(fused_codes[0])
            
            # Si on a une expected_char, vérifier qu'elle correspond
            # Si expected_char est None ou vide, accepter la fusion si c'est une lettre valide (non-bruit)
            if expected_char and expected_char != '':
                if fused_char == expected_char:
                    # Succès !
                    return CorrectionResult(
                        success=True,
                        new_rects=[fused_rect],
                        new_codes=[fused_codes[0]],
                        num_rects_to_replace=num_rects,
                        metadata={
                            'rect_to_replace_idx': rect_idx,  # Index du premier rectangle à remplacer
                            'num_rects_fused': num_rects,
                            'detected_chars': detected_chars,
                            'fused_char': fused_char
                        }
                    )
            else:
                # Pas d'expected_char fourni - accepter la fusion si c'est une lettre valide (non-bruit)
                # La validation se fera dans text_alignment.py en comparant avec les lettres attendues
                return CorrectionResult(
                    success=True,
                    new_rects=[fused_rect],
                    new_codes=[fused_codes[0]],
                    num_rects_to_replace=num_rects,
                    metadata={
                        'num_rects_fused': num_rects,
                        'detected_chars': detected_chars,
                        'fused_char': fused_char
                    }
                )
        
        return CorrectionResult(success=False, metadata={'reason': 'Fusion did not give expected letter'})

