"""
Gestionnaire de corrections : choisit intelligemment la méthode de correction à utiliser.
"""
from typing import List, Tuple, Optional
import numpy as np
from BE_Model_Cursor.corrections.base_correction import BaseCorrection, CorrectionResult
from BE_Model_Cursor.corrections.height_extension_correction import HeightExtensionCorrection
from BE_Model_Cursor.corrections.fusion_correction import FusionCorrection
from BE_Model_Cursor.corrections.reunification_correction import ReunificationCorrection
from BE_Model_Cursor.corrections.missing_letter_correction import MissingLetterCorrection


class CorrectionManager:
    """
    Gestionnaire qui choisit intelligemment la méthode de correction à utiliser
    en fonction du contexte (type d'erreur, nombre de rectangles, caractères détectés/attendus).
    
    La logique de sélection est basée sur le code existant dans letter_detection.py :
    - Si N rectangles (N >= 2) détectés au lieu d'1 attendue → FusionCorrection
    - Si 1 rectangle détecté au lieu d'1 attendue :
      - Si détecté='ה' et attendu='ק' → HeightExtensionCorrection (puis ReunificationCorrection si échec)
      - Sinon → ReunificationCorrection
    """
    
    def __init__(self, image: np.ndarray, weight_file: str):
        """
        Args:
            image: Image OpenCV complète
            weight_file: Chemin vers le fichier de poids du modèle
        """
        self.image = image
        self.weight_file = weight_file
        
        # Initialiser les méthodes de correction disponibles (sans ordre fixe)
        self.height_extension = HeightExtensionCorrection(image, weight_file)
        self.fusion = FusionCorrection(image, weight_file)
        self.reunification = ReunificationCorrection(image, weight_file)
        self.missing_letter = MissingLetterCorrection(image, weight_file)
    
    def try_correct_error(self, rect_idx: int, valid_rects_final: List[Tuple[int, int, int, int]],
                          valid_codes: List[int], expected_char: str, detected_char: str,
                          detected_chars: Optional[str] = None,
                          reference_text: str = '', detected_text: str = '') -> Optional[CorrectionResult]:
        """
        Essaie de corriger une erreur en choisissant la bonne méthode selon le contexte.
        
        Args:
            rect_idx: Index du rectangle à corriger
            valid_rects_final: Liste des rectangles actuels
            valid_codes: Liste des codes de lettres actuels
            expected_char: Lettre attendue (1 lettre)
            detected_char: Lettre détectée (pour 1 rectangle)
            detected_chars: Chaîne de caractères détectés (pour N rectangles, ex: "צלי")
            reference_text: Texte de référence complet
            detected_text: Texte détecté actuel
        
        Returns:
            CorrectionResult si une méthode a réussi, None sinon
        """
        # CAS 1: N rectangles (N >= 2) détectés au lieu d'1 lettre attendue → Fusion
        if detected_chars and len(detected_chars) >= 2 and len(expected_char) == 1:
            # Exemple: "צלי" (3 rectangles) détectés au lieu de "ז" (1 lettre) attendue
            print(f"[CorrectionManager] CAS 1: {len(detected_chars)} rectangles détectés au lieu d'1 lettre attendue → Tentative de fusion")
            try:
                result = self.fusion.try_correct(
                    rect_idx=rect_idx,
                    valid_rects_final=valid_rects_final,
                    valid_codes=valid_codes,
                    expected_char=expected_char,
                    detected_char=detected_char,
                    reference_text=reference_text,
                    detected_text=detected_text,
                    detected_chars=detected_chars
                )
                if result.success:
                    return result
            except Exception as e:
                print(f"  → ✗ Erreur dans FusionCorrection: {e}")
            return None
        
        # CAS 3: Lettre manquante (pas de rectangle correspondant) - vérifier en premier
        # Si detected_char est vide, c'est une lettre manquante
        if not detected_char or detected_char == '':
            print(f"[CorrectionManager] CAS 3: Lettre manquante → Tentative de réunification")
            try:
                result = self.missing_letter.try_correct(
                    rect_idx=rect_idx,
                    valid_rects_final=valid_rects_final,
                    valid_codes=valid_codes,
                    expected_char=expected_char,
                    detected_char=detected_char,
                    reference_text=reference_text,
                    detected_text=detected_text
                )
                if result.success:
                    return result
            except Exception as e:
                print(f"  → ✗ Erreur dans MissingLetterCorrection: {e}")
            return None
        
        # CAS 2: 1 rectangle détecté au lieu d'1 lettre attendue → Solution simple puis Réunification
        if len(expected_char) == 1 and (detected_chars is None or len(detected_chars) == 1):
            # Sous-cas 2.1: Si détecté='ה' et attendu='ק' → Essayer d'abord la solution simple (extension de hauteur)
            if detected_char == 'ה' and expected_char == 'ק':
                print(f"[CorrectionManager] CAS 2.1: 'ה' détecté au lieu de 'ק' → Tentative d'extension de hauteur")
                try:
                    result = self.height_extension.try_correct(
                        rect_idx=rect_idx,
                        valid_rects_final=valid_rects_final,
                        valid_codes=valid_codes,
                        expected_char=expected_char,
                        detected_char=detected_char,
                        reference_text=reference_text,
                        detected_text=detected_text
                    )
                    if result.success:
                        return result
                except Exception as e:
                    print(f"  → ✗ Erreur dans HeightExtensionCorrection: {e}")
            
            # Sous-cas 2.2: Solution simple échouée (ou non applicable) → Réunification
            print(f"[CorrectionManager] CAS 2.2: 1 rectangle détecté au lieu d'1 lettre attendue → Tentative de réunification")
            try:
                result = self.reunification.try_correct(
                    rect_idx=rect_idx,
                    valid_rects_final=valid_rects_final,
                    valid_codes=valid_codes,
                    expected_char=expected_char,
                    detected_char=detected_char,
                    reference_text=reference_text,
                    detected_text=detected_text
                )
                if result.success:
                    return result
            except Exception as e:
                print(f"  → ✗ Erreur dans ReunificationCorrection: {e}")
            return None
        
        # Cas non géré
        print(f"[CorrectionManager] ⚠️  Cas non géré: expected_char='{expected_char}', detected_char='{detected_char}', detected_chars='{detected_chars}'")
        return None
    
    def add_correction_method(self, correction_method: BaseCorrection):
        """
        Ajoute une nouvelle méthode de correction à la liste.
        
        Args:
            correction_method: Instance d'une sous-classe de BaseCorrection
        """
        self.correction_methods.append(correction_method)

