import cv2
import numpy as np
from typing import Tuple, Union, Optional, List
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.utils.rect_refiner import RectRefiner

class WidthRefinementCorrection(BaseCorrection):
    """
    Classe pour raffiner la largeur des rectangles détectés.
    """
    
    def __init__(self, image: np.ndarray, weight_file: str = None, debug: bool = False):
        """
        Args:
            image: Image OpenCV complète (numpy array) en couleur BGR
            weight_file: Chemin vers les poids du modèle (optionnel, pour compatibilité)
            debug: Si True, active les logs détaillés
        """
        super().__init__(image, weight_file)
        self.debug = debug
        
    def try_correct(self, rect_idx: int, valid_rects_final: List[Union[Tuple[int, int, int, int], RectangleWithLine]],
                    valid_codes: List[int], expected_char: str, detected_char: str,
                    reference_text: str = '', detected_text: str = '', 
                    detected_chars: Optional[str] = None) -> CorrectionResult:
        
        if not valid_rects_final or rect_idx >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={"reason": "Invalid rect_idx"})
            
        rect = valid_rects_final[rect_idx]
        
        # Tenter de raffiner le rectangle en utilisant RectRefiner
        refined_rects = RectRefiner.refine_rect(self.image, rect)
        
        # Vérifier si on a un changement significatif
        if not refined_rects:
             return CorrectionResult(success=False, metadata={"reason": "Refinement failed (empty)"})

        # Si refined_rects contient exactement le même objet (pas de changement)
        # RectRefiner retourne [rect] si pas de changement
        if len(refined_rects) == 1:
            refined = refined_rects[0]
            
            # Comparer la largeur
            w_old = rect.w if isinstance(rect, RectangleWithLine) else rect[2]
            w_new = refined.w if isinstance(refined, RectangleWithLine) else refined[2]
            
            if w_new < w_old: # Si la largeur a diminué (RectRefiner s'assure déjà que c'est significatif)
                 return CorrectionResult(success=True, new_rects=[refined], num_rects_to_replace=1,
                                         metadata={"type": "shrink", "w_old": w_old, "w_new": w_new})
            else:
                 return CorrectionResult(success=False, metadata={"reason": "No width reduction"})
            
        # Cas 1: Splitting (plusieurs rectangles retournés)
        if len(refined_rects) > 1:
             return CorrectionResult(success=True, new_rects=refined_rects, num_rects_to_replace=1, 
                                     metadata={"type": "split", "count": len(refined_rects)})
                                     
        return CorrectionResult(success=False, metadata={"reason": "No significant change"})

    def refine_rect(self, rect: Union[Tuple[int, int, int, int], RectangleWithLine]) -> List[Union[Tuple[int, int, int, int], RectangleWithLine]]:
        """
        Wrapper pour RectRefiner.refine_rect pour compatibilité si nécessaire.
        """
        return RectRefiner.refine_rect(self.image, rect)
