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
from BE_Model_Cursor.utils.logger import get_logger
from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew


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
        self.logger = get_logger(__name__)
    
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
            self.logger.debug(f"[CorrectionManager] CAS 1: {len(detected_chars)} rectangles détectés au lieu d'1 lettre attendue → Tentative de fusion")
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
                    # Vérification finale : s'assurer que la correction donne bien la lettre attendue
                    if expected_char and expected_char != '':
                        from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew
                        new_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                        if new_char != expected_char:
                            self.logger.debug(f"[CorrectionManager] Fusion donne '{new_char}' mais attendu '{expected_char}' → rejetée")
                            return None
                    return result
            except Exception as e:
                self.logger.error(f"Erreur dans FusionCorrection: {e}")
            return None
        
        # CAS 3: Lettre manquante (pas de rectangle correspondant) - vérifier en premier
        # Si detected_char est vide, c'est une lettre manquante
        if not detected_char or detected_char == '':
            # Vérifier si c'est UNE seule lettre manquante
            # Si plusieurs lettres manquent, c'est probablement une paracha partielle
            # et la réunification ne peut pas trouver plusieurs lettres en une fois
            if len(expected_char) > 1:
                self.logger.debug(f"[CorrectionManager] CAS 3: {len(expected_char)} lettres manquantes '{expected_char}' → "
                                f"Paracha partielle probable, réunification non applicable")
                return None
            
            # Une seule lettre manquante → on peut essayer la réunification
            self.logger.debug(f"[CorrectionManager] CAS 3: 1 lettre manquante '{expected_char}' → Tentative de réunification")
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
                    # Vérification finale : s'assurer que la correction contient bien la lettre attendue
                    if expected_char and expected_char != '':
                        from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew
                        detected_chars_in_result = [letter_code_to_hebrew(code) for code in result.new_codes if code != 27]
                        if expected_char not in detected_chars_in_result:
                            self.logger.debug(f"[CorrectionManager] MissingLetter ne contient pas '{expected_char}' → rejetée")
                            return None
                    return result
            except Exception as e:
                print(f"  → ✗ Erreur dans MissingLetterCorrection: {e}")
            return None
        
        # CAS 3: 1 rectangle détecté au lieu de N lettres attendues (Substitution 1->N)
        # Exemple: 1 rectangle contient "של" collés, attendu "של" (2 lettres)
        if len(expected_char) > 1 and detected_char and detected_char != '':
            self.logger.debug(f"[CorrectionManager] CAS 3: 1 rectangle '{detected_char}' au lieu de '{expected_char}' → Tentative de réunification multiple")
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
                    # Vérification finale
                    from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew
                    detected_str = "".join([letter_code_to_hebrew(c) for c in result.new_codes if c != 27])
                    if detected_str == expected_char:
                        return result
                    else:
                        self.logger.debug(f"[CorrectionManager] Reunification multiple donne '{detected_str}' mais attendu '{expected_char}' → rejetée")
            except Exception as e:
                self.logger.error(f"Erreur dans ReunificationCorrection (Multiple): {e}")

        # CAS 2: 1 rectangle détecté au lieu d'1 lettre attendue → Solution simple puis Réunification
        if len(expected_char) == 1 and (detected_chars is None or len(detected_chars) == 1):
            # Sous-cas 2.1: Si détecté='ה' et attendu='ק' → Essayer d'abord la solution simple (extension de hauteur)
            if detected_char == 'ה' and expected_char == 'ק':
                self.logger.debug(f"[CorrectionManager] CAS 2.1: 'ה' détecté au lieu de 'ק' → Tentative d'extension de hauteur")
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
                        # Vérification finale : s'assurer que la correction donne bien la lettre attendue
                        if expected_char and expected_char != '':
                            from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew
                            new_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                            if new_char != expected_char:
                                self.logger.debug(f"[CorrectionManager] HeightExtension donne '{new_char}' mais attendu '{expected_char}' → rejetée")
                                result = None
                        if result and result.success:
                            return result
                except Exception as e:
                    print(f"  → ✗ Erreur dans HeightExtensionCorrection: {e}")
            
            # Sous-cas 2.2: Solution simple échouée (ou non applicable) → Réunification
            self.logger.debug(f"[CorrectionManager] CAS 2.2: 1 rectangle détecté au lieu d'1 lettre attendue → Tentative de réunification")
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
                    # Vérification finale : s'assurer que la correction donne bien la lettre attendue
                    # Pour réunification, on vérifie que expected_char est dans les lettres détectées
                    if expected_char and expected_char != '':
                        from BE_Model_Cursor.models.letter_predictor import letter_code_to_hebrew
                        detected_chars_in_result = [letter_code_to_hebrew(code) for code in result.new_codes if code != 27]
                        if expected_char not in detected_chars_in_result:
                            self.logger.debug(f"[CorrectionManager] Reunification ne contient pas '{expected_char}' → rejetée")
                            return None
                    return result
            except Exception as e:
                print(f"  → ✗ Erreur dans ReunificationCorrection: {e}")
            return None
        
        # Cas non géré
        self.logger.warning(f"[CorrectionManager] Cas non géré: expected_char='{expected_char}', detected_char='{detected_char}', detected_chars='{detected_chars}'")
        return None
    
    def _apply_correction_result(self, corrected_rects: List, corrected_codes: List[int], rect_idx: int, correction_result: CorrectionResult):
        """
        Applique le résultat d'une correction réussie.
        
        Args:
            corrected_rects: Liste des rectangles (modifiée en place)
            corrected_codes: Liste des codes (modifiée en place)
            rect_idx: Index du rectangle à remplacer
            correction_result: CorrectionResult avec les nouveaux rectangles et codes
        """
        from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
        
        # Déterminer l'index du rectangle à remplacer
        replace_idx = correction_result.metadata.get('rect_to_replace_idx', rect_idx)
        
        # Déterminer le line_number à utiliser pour les nouveaux rectangles
        # Utiliser le line_number du rectangle à remplacer, ou celui du rectangle précédent/suivant
        line_number = None
        if replace_idx < len(corrected_rects):
            if isinstance(corrected_rects[replace_idx], RectangleWithLine):
                line_number = corrected_rects[replace_idx].line_number
        elif replace_idx > 0 and replace_idx - 1 < len(corrected_rects):
            if isinstance(corrected_rects[replace_idx - 1], RectangleWithLine):
                line_number = corrected_rects[replace_idx - 1].line_number
        elif len(corrected_rects) > 0:
            if isinstance(corrected_rects[0], RectangleWithLine):
                line_number = corrected_rects[0].line_number
        
        # Si on n'a toujours pas de line_number, utiliser 0 par défaut
        if line_number is None:
            line_number = 0
        
        # Remplacer les rectangles
        # IMPORTANT: Supprimer du plus grand index vers le plus petit pour éviter le décalage des indices
        # Si on doit supprimer N rectangles à partir de replace_idx, on supprime replace_idx+N-1, puis replace_idx+N-2, etc.
        for i in range(correction_result.num_rects_to_replace - 1, -1, -1):
            idx_to_remove = replace_idx + i
            if idx_to_remove < len(corrected_rects):
                corrected_rects.pop(idx_to_remove)
                corrected_codes.pop(idx_to_remove)
        
        # Insérer les nouveaux rectangles (en ordre inverse pour l'hébreu)
        # Convertir les tuples en RectangleWithLine avec detected_letter
        # Les rectangles corrigés sont marqués en vert (correct) car la correction a réussi
        for j in range(len(correction_result.new_rects) - 1, -1, -1):
            new_rect = correction_result.new_rects[j]
            new_code = correction_result.new_codes[j]
            detected_letter = letter_code_to_hebrew(new_code) if new_code != 27 else None
            
            # Si new_rect est déjà un RectangleWithLine, mettre à jour detected_letter, line_number et color
            if isinstance(new_rect, RectangleWithLine):
                new_rect.detected_letter = detected_letter
                new_rect.line_number = line_number
                new_rect.color = (0, 255, 0)  # Vert = correction réussie
                # text_position sera mis à jour après l'insertion
                corrected_rects.insert(replace_idx, new_rect)
            else:
                # Créer un nouveau RectangleWithLine (text_position sera mis à jour après l'insertion)
                # Couleur verte car la correction a réussi
                rect_with_line = RectangleWithLine(new_rect[0], new_rect[1], new_rect[2], new_rect[3], line_number, detected_letter, None, (0, 255, 0))
                corrected_rects.insert(replace_idx, rect_with_line)
            
            corrected_codes.insert(replace_idx, new_code)
        
        # Réindexer tous les rectangles pour maintenir text_position cohérent
        for i, rect in enumerate(corrected_rects):
            if isinstance(rect, RectangleWithLine):
                rect.text_position = i
    
    def try_and_apply_correction(self, corrected_rects: List, corrected_codes: List[int], rect_idx: int,
                                  expected_char: str, detected_char: str,
                                  detected_chars: Optional[str] = None,
                                  reference_text: str = '', detected_text: str = '') -> bool:
        """
        Essaie de corriger une erreur ET applique le résultat si succès.
        
        Cette méthode combine try_correct_error() et _apply_correction_result() pour simplifier l'usage.
        
        Args:
            corrected_rects: Liste des rectangles (modifiée en place si correction réussie)
            corrected_codes: Liste des codes (modifiée en place si correction réussie)
            rect_idx: Index du rectangle à corriger
            expected_char: Lettre attendue (1 lettre)
            detected_char: Lettre détectée (pour 1 rectangle)
            detected_chars: Chaîne de caractères détectés (pour N rectangles, ex: "צלי")
            reference_text: Texte de référence complet
            detected_text: Texte détecté actuel
        
        Returns:
            True si la correction a été appliquée avec succès, False sinon
        """
        result = self.try_correct_error(
            rect_idx=rect_idx,
            valid_rects_final=corrected_rects,
            valid_codes=corrected_codes,
            expected_char=expected_char,
            detected_char=detected_char,
            detected_chars=detected_chars,
            reference_text=reference_text,
            detected_text=detected_text
        )
        
        if result and result.success:
            self._apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
            return True
        
        return False
    
    def add_correction_method(self, correction_method: BaseCorrection):
        """
        Ajoute une nouvelle méthode de correction à la liste.
        
        Args:
            correction_method: Instance d'une sous-classe de BaseCorrection
        """
        self.correction_methods.append(correction_method)

