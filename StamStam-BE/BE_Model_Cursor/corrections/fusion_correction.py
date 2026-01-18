"""
Méthode de correction : Fusion de N rectangles en 1 lettre.
"""
from typing import List, Tuple
import numpy as np
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.utils.contour_detector import union_rect


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
        
        # Fusionner tous les rectangles (N rectangles en 1)
        # Commencer avec le premier rectangle
        fused_rect = valid_rects_final[rect_idx]
        for j in range(1, num_rects):
            rect_j = valid_rects_final[rect_idx + j]
            fused_rect = union_rect(fused_rect, rect_j)
        
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
                            'num_rects_fused': num_rects,
                            'detected_chars': detected_chars,
                            'fused_char': fused_char
                        }
                    )
            else:
                # Pas d'expected_char, accepter la fusion si c'est une lettre valide
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

