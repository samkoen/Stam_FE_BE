"""
Méthode de correction : Extension de hauteur pour le cas ה→ק.
"""
from typing import List, Tuple, Optional
import numpy as np
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew


class HeightExtensionCorrection(BaseCorrection):
    """
    Correction pour le cas ה→ק : allonger la hauteur du rectangle de 30-50%.
    
    Cette méthode est spécifique au cas où 'ה' est détecté au lieu de 'ק',
    car ces deux lettres se ressemblent et diffèrent principalement par leur hauteur.
    """
    
    def __init__(self, image: np.ndarray, weight_file: str, height_increases: List[float] = None):
        """
        Args:
            image: Image OpenCV complète
            weight_file: Chemin vers le fichier de poids du modèle
            height_increases: Liste des pourcentages d'augmentation à essayer (défaut: [0.30, 0.35, 0.40, 0.45, 0.50])
        """
        super().__init__(image, weight_file)
        self.height_increases = height_increases or [0.30, 0.35, 0.40, 0.45, 0.50]
    
    def try_correct(self, rect_idx: int, valid_rects_final: List[Tuple[int, int, int, int]],
                   valid_codes: List[int], expected_char: str, detected_char: str,
                   reference_text: str = '', detected_text: str = '', 
                   detected_chars: Optional[str] = None) -> CorrectionResult:
        """
        Tente de corriger en allongeant la hauteur du rectangle.
        
        UNIQUEMENT pour le cas 'ה' détecté au lieu de 'ק'.
        """
        # Vérifier que c'est le bon cas
        if detected_char != 'ה' or expected_char != 'ק':
            return CorrectionResult(success=False, metadata={'reason': 'Not the ה→ק case'})
        
        if rect_idx >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={'reason': 'Invalid rect_idx'})
        
        x, y, w, h = valid_rects_final[rect_idx]
        
        # Essayer chaque pourcentage d'augmentation
        for height_increase in self.height_increases:
            # Allonger la hauteur (augmenter h seulement, garder y inchangé)
            new_h = int(h * (1 + height_increase))
            
            # Vérifier que le rectangle ne dépasse pas les limites de l'image
            if y + new_h > self.image.shape[0]:
                new_h = self.image.shape[0] - y
            
            if new_h > h:  # S'assurer qu'on a bien augmenté la hauteur
                extended_rect = (x, y, w, new_h)  # y reste inchangé
                
                # Prédire la lettre sur le rectangle allongé
                extended_rects = [extended_rect]
                extended_codes = predict_letters(self.image, extended_rects, self.weight_file)
                
                if len(extended_codes) > 0 and extended_codes[0] != 27:
                    extended_char = letter_code_to_hebrew(extended_codes[0])
                    
                    if extended_char == expected_char:
                        # Succès !
                        return CorrectionResult(
                            success=True,
                            new_rects=[extended_rect],
                            new_codes=[extended_codes[0]],
                            num_rects_to_replace=1,
                            metadata={
                                'height_increase': height_increase,
                                'original_h': h,
                                'new_h': new_h,
                                'detected_char': extended_char
                            }
                        )
        
        return CorrectionResult(success=False, metadata={'reason': 'No height increase gave the expected letter'})

