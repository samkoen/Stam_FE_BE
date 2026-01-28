import cv2
import numpy as np
from typing import List, Union, Tuple, Optional
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.utils.rect_refiner import RectRefiner
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew

class SplitSubstitutionCorrection(BaseCorrection):
    """
    Tente de corriger une substitution en divisant le rectangle détecté en plusieurs lettres.
    Utile pour le cas où deux lettres sont collées (ex: 'הם' détecté comme 'ת').
    Utilise RectRefiner pour séparer les formes.
    """
    
    def __init__(self, image: np.ndarray, weight_file: str = None, debug: bool = False):
        super().__init__(image, weight_file)
        self.debug = debug
        
    def try_correct(self, rect_idx: int, valid_rects_final: List[Union[Tuple[int, int, int, int], RectangleWithLine]],
                    valid_codes: List[int], expected_char: str, detected_char: str,
                    reference_text: str = '', detected_text: str = '', 
                    detected_chars: Optional[str] = None) -> CorrectionResult:
        
        if not valid_rects_final or rect_idx >= len(valid_rects_final):
            return CorrectionResult(success=False, metadata={"reason": "Invalid rect_idx"})
            
        rect = valid_rects_final[rect_idx]
        
        # 1. Utiliser RectRefiner pour voir si on peut diviser le rectangle
        refined_rects = RectRefiner.refine_rect(self.image, rect)
        
        # Si pas de splitting, on ne peut rien faire ici
        if len(refined_rects) <= 1:
            return CorrectionResult(success=False, metadata={"reason": "No split detected by RectRefiner"})
            
        if self.debug:
            print(f"[SplitSubstitutionCorrection] Splitting détecté : 1 rectangle -> {len(refined_rects)} rectangles")
            
        # 2. Prédire les lettres sur les nouveaux rectangles
        # Préparer les inputs pour predict_letters
        # predict_letters attend une liste de rectangles (tuples ou objets)
        
        # Convertir en format attendu par predict_letters si nécessaire (il supporte les deux)
        new_codes = predict_letters(self.image, refined_rects, self.weight_file)
        
        if not new_codes or len(new_codes) != len(refined_rects):
             return CorrectionResult(success=False, metadata={"reason": "Prediction failed on new rects"})
             
        # 3. Vérifier si ça correspond à ce qu'on attend
        # expected_char peut contenir plusieurs lettres (ex: "הם")
        
        predicted_chars = "".join([letter_code_to_hebrew(code) if code != 27 else '' for code in new_codes])
        
        # Critère de succès :
        # - Si expected_char est fourni, on veut que ça matche (ou s'en approche fortement)
        # - Sinon (correction aveugle), on espère juste avoir des lettres valides (pas 27)
        
        success = False
        if expected_char:
            # Comparaison exacte ou partielle ?
            # Pour l'instant, exacte ou si expected_char est inclus dans predicted_chars
            if predicted_chars == expected_char:
                success = True
            elif len(predicted_chars) == len(expected_char) and predicted_chars == expected_char:
                success = True
            # Cas spécial : "הם" vs "ת" -> si on trouve "ה" et "ם", c'est gagné
        else:
            # Pas de cible explicite, on accepte si on a trouvé des lettres valides
            if len(predicted_chars) == len(refined_rects): # Toutes valides
                success = True
                
        if success:
            # Mettre à jour les rectangles avec les nouvelles lettres détectées
            final_rects = []
            final_codes = []
            
            for i, (new_rect, new_code) in enumerate(zip(refined_rects, new_codes)):
                detected_letter = letter_code_to_hebrew(new_code)
                
                if isinstance(new_rect, RectangleWithLine):
                    new_rect.detected_letter = detected_letter
                    # On garde la couleur originale ou on met vert ? Vert car corrigé.
                    new_rect.color = (0, 255, 0) 
                    final_rects.append(new_rect)
                else:
                    # Si c'était un tuple, on le renvoie tel quel (ou on pourrait le promouvoir en RectangleWithLine)
                    # Pour compatibilité stricte, on renvoie ce qu'on a reçu (tuple ou obj)
                    # Mais RectRefiner retourne le même type que l'entrée.
                    final_rects.append(new_rect)
                
                final_codes.append(new_code)
                
            return CorrectionResult(
                success=True,
                new_rects=final_rects,
                new_codes=final_codes,
                num_rects_to_replace=1, # On remplace 1 vieux par N nouveaux
                metadata={"type": "split_substitution", "predicted": predicted_chars}
            )
            
        return CorrectionResult(success=False, metadata={"reason": f"Prediction mismatch: got '{predicted_chars}', expected '{expected_char}'"})

