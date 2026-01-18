"""
Module pour aligner le texte détecté avec le texte original et résoudre les problèmes de segmentation
"""
import diff_match_patch as dmp_module
import cv2
import numpy as np
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.corrections.correction_manager import CorrectionManager
from BE_Model_Cursor.corrections.base_correction import CorrectionResult
from BE_Model_Cursor.corrections.fusion_correction import FusionCorrection
from BE_Model_Cursor.utils.logger import get_logger


def align_text_with_reference(detected_text, reference_text, letter_rects, letter_codes, image, weight_file, debug=False):
    """
    Aligne le texte détecté avec le texte de référence et identifie les problèmes de segmentation.
    Utilise CorrectionManager pour toutes les corrections avancées.
    
    Args:
        detected_text: Texte hébreu détecté (string)
        reference_text: Texte de référence (texte original de la paracha)
        letter_rects: Liste des rectangles détectés [(x, y, w, h), ...]
        letter_codes: Liste des codes de lettres détectées [code1, code2, ...]
        image: Image OpenCV (numpy array)
        weight_file: Chemin vers le fichier de poids du modèle
        debug: Si True, affiche des logs détaillés
        
    Returns:
        tuple: (corrected_rects, corrected_codes, corrections_applied)
               où corrections_applied est une liste de corrections effectuées
    """
    dmp = dmp_module.diff_match_patch()
    
    corrected_rects = list(letter_rects)
    corrected_codes = list(letter_codes)
    corrections_applied = []
    correction_manager = CorrectionManager(image, weight_file)
    fusion_correction = FusionCorrection(image, weight_file)  # Pour les fusions simples
    
    # Initialiser le logger
    logger = get_logger(__name__, debug=debug)
    
    # Utiliser une boucle while pour recalculer le diff après chaque correction
    max_iterations = 100
    iteration = 0
    
    if debug:
        logger.debug(f"Début de l'alignement avec CorrectionManager")
        logger.debug(f"Texte de référence (longueur: {len(reference_text)}): {reference_text[:100]}...")
        logger.debug(f"Texte détecté initial (longueur: {len(detected_text)}): {detected_text[:100]}...")
        logger.debug(f"Nombre de rectangles: {len(corrected_rects)}")
    
    while iteration < max_iterations:
        iteration += 1
        
        # Recalculer le texte détecté et le diff à chaque itération
        detected_text_normalized = ''.join([letter_code_to_hebrew(code) if code != 27 else '' 
                                           for code in corrected_codes])
        diff = dmp.diff_main(reference_text, detected_text_normalized)
        dmp.diff_cleanupSemantic(diff)
        
        if debug and iteration == 1:
            logger.debug(f"Diff initial calculé avec {len(diff)} opérations")
        elif debug and iteration > 1:
            logger.debug(f"Itération {iteration}: Diff recalculé avec {len(diff)} opérations après correction")
        
        # Parcourir les différences pour identifier les problèmes
        rect_idx = 0
        diff_changed = False
        
        for diff_idx, (op, text) in enumerate(diff):
            if op == 0:  # Égalité - texte correct
                if debug:
                    detected_char = detected_text_normalized[rect_idx] if rect_idx < len(detected_text_normalized) else None
                    detected_char_hebrew = letter_code_to_hebrew(corrected_codes[rect_idx]) if rect_idx < len(corrected_codes) else None
                    logger.debug(f"[Comparaison] Position {rect_idx}: ✓ BONNE LETTRE '{detected_char_hebrew}' (code: {corrected_codes[rect_idx] if rect_idx < len(corrected_codes) else 'N/A'})")
                
                rect_idx += len(text)
                
            elif op == -1:  # Supprimé dans détecté = lettre manquante ou substitution
                expected_char = text[0] if text else None
                
                # Vérifier si c'est une substitution (suivi d'une addition)
                is_substitution = (diff_idx + 1 < len(diff) and diff[diff_idx + 1][0] == 1)
                
                if is_substitution:
                    # C'est une substitution : une lettre a été remplacée par une autre
                    added_text = diff[diff_idx + 1][1]
                    expected_text = text
                    
                    if debug:
                        detected_char = added_text[0] if added_text else None
                        detected_char_hebrew = letter_code_to_hebrew(corrected_codes[rect_idx]) if rect_idx < len(corrected_codes) else None
                        logger.debug(f"[Comparaison] Position {rect_idx}: ✗ LETTRE FAUSSE - détecté '{detected_char_hebrew}' au lieu de '{expected_char}'")
                    
                    # CAS 1: N rectangles détectés au lieu d'1 lettre attendue
                    if len(added_text) >= 2 and len(expected_text) == 1 and rect_idx + len(added_text) - 1 < len(corrected_rects):
                        expected_char = expected_text[0]
                        detected_chars = added_text
                        
                        if debug:
                            logger.debug(f"→ 1ère tentative: Fusion de {len(detected_chars)} rectangles pour obtenir '{expected_char}'...")
                        
                        # Utiliser CorrectionManager pour tenter la fusion
                        result = correction_manager.try_correct_error(
                            rect_idx=rect_idx,
                            valid_rects_final=corrected_rects,
                            valid_codes=corrected_codes,
                            expected_char=expected_char,
                            detected_char=detected_chars[0] if detected_chars else '',
                            detected_chars=detected_chars,
                            reference_text=reference_text,
                            detected_text=detected_text_normalized
                        )
                        
                        if result and result.success:
                            if debug:
                                new_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                                logger.debug(f"✓ SUCCÈS: Fusion réussie, '{detected_chars}' -> '{new_char}'")
                            
                            _apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
                            corrections_applied.append({
                                'type': 'fusion_correction',
                                'position': rect_idx,
                                'text': text
                            })
                            diff_changed = True
                            break  # Recalculer le diff
                        elif debug:
                            logger.debug(f"✗ ÉCHEC: Fusion de {len(detected_chars)} rectangles n'a pas donné '{expected_char}'")
                    
                    # CAS 2: 1 rectangle détecté au lieu d'1 lettre attendue (extension hauteur ou réunification)
                    elif len(added_text) == 1 and len(expected_text) == 1 and rect_idx < len(corrected_rects):
                        expected_char = expected_text[0]
                        detected_char = added_text[0]
                        
                        if debug:
                            logger.debug(f"→ 1ère tentative: Correction avec CorrectionManager (extension hauteur ou réunification)...")
                        
                        # Sauvegarder l'état initial
                        saved_rects = corrected_rects[:]
                        saved_codes = corrected_codes[:]
                        
                        # Utiliser CorrectionManager
                        result = correction_manager.try_correct_error(
                            rect_idx=rect_idx,
                            valid_rects_final=corrected_rects,
                            valid_codes=corrected_codes,
                            expected_char=expected_char,
                            detected_char=detected_char,
                            reference_text=reference_text,
                            detected_text=detected_text_normalized
                        )
                        
                        if result and result.success:
                            if debug:
                                new_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                                logger.debug(f"✓ SUCCÈS: Correction réussie, '{detected_char}' -> '{new_char}'")
                            
                            _apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
                            corrections_applied.append({
                                'type': 'wrong_letter_correction',
                                'position': rect_idx,
                                'text': text
                            })
                            diff_changed = True
                            break  # Recalculer le diff
                        else:
                            # Restaurer l'état initial
                            corrected_rects[:] = saved_rects
                            corrected_codes[:] = saved_codes
                            if debug:
                                logger.debug(f"✗ ÉCHEC: Correction n'a pas fonctionné")
                    
                    # Avancer dans le diff pour passer l'opération d'addition aussi
                    diff_idx += 1
                
                else:
                    # Vraie lettre manquante (pas de rectangle correspondant)
                    expected_char = text[0] if text else None
                    
                    if debug:
                        logger.debug(f"[Comparaison] Position {rect_idx}: ⚠ LETTRE MANQUANTE '{expected_char}'")
                        logger.debug(f"→ 1ère tentative: Correction avec CorrectionManager (MissingLetterCorrection)...")
                    
                    # Utiliser CorrectionManager pour tenter la correction
                    result = correction_manager.try_correct_error(
                        rect_idx=rect_idx,
                        valid_rects_final=corrected_rects,
                        valid_codes=corrected_codes,
                        expected_char=expected_char,
                        detected_char='',  # Pas de lettre détectée pour une lettre manquante
                        reference_text=reference_text,
                        detected_text=detected_text_normalized
                    )
                    
                    if result and result.success:
                        if debug:
                            new_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                            logger.debug(f"✓ SUCCÈS: Lettre manquante trouvée, -> '{new_char}'")
                        
                        _apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
                        corrections_applied.append({
                            'type': 'missing_letter_correction',
                            'position': rect_idx,
                            'text': text
                        })
                        diff_changed = True
                        break  # Recalculer le diff
                    elif debug:
                        logger.debug(f"✗ ÉCHEC: Lettre manquante '{expected_char}' non trouvée")
                
            elif op == 1:  # Ajouté dans détecté = lettre en trop
                if debug:
                    detected_char = letter_code_to_hebrew(corrected_codes[rect_idx]) if rect_idx < len(corrected_codes) else None
                    logger.debug(f"[Comparaison] Position {rect_idx}: + LETTRE EN TROP '{detected_char}'")
                
                # Essayer fusion simple avec FusionCorrection (fusionner 2 rectangles en 1)
                # Tester les deux possibilités : fusionner avec i-1 ou avec i+1
                if rect_idx > 0 and rect_idx < len(corrected_rects):
                    detected_char = letter_code_to_hebrew(corrected_codes[rect_idx]) if rect_idx < len(corrected_codes) else ''
                    
                    # Tentative 1: Fusionner rect_idx-1 et rect_idx
                    if rect_idx > 0:
                        detected_chars_im1_i = (letter_code_to_hebrew(corrected_codes[rect_idx - 1]) if rect_idx - 1 < len(corrected_codes) else '') + detected_char
                        
                        if debug:
                            logger.debug(f"→ 1ère tentative: Fusion avec FusionCorrection (rect_idx-1 + rect_idx = '{detected_chars_im1_i}')...")
                        
                        result = fusion_correction.try_correct(
                            rect_idx=rect_idx - 1,
                            valid_rects_final=corrected_rects,
                            valid_codes=corrected_codes,
                            expected_char='',  # Pas d'expected_char pour les lettres en trop
                            detected_char=detected_char,
                            detected_chars=detected_chars_im1_i,
                            reference_text=reference_text,
                            detected_text=detected_text_normalized
                        )
                        
                        if result and result.success:
                            if debug:
                                fused_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                                logger.debug(f"✓ SUCCÈS: Fusion rect_idx-1 + rect_idx réussie -> '{fused_char}'")
                            
                            _apply_correction_result(corrected_rects, corrected_codes, rect_idx - 1, result)
                            corrections_applied.append({
                                'type': 'fusion',
                                'position': rect_idx - 1,
                                'fusion_type': 'im1_i',
                                'text': text
                            })
                            diff_changed = True
                            break  # Recalculer le diff
                        elif debug:
                            logger.debug(f"✗ ÉCHEC: Fusion rect_idx-1 + rect_idx n'a pas fonctionné")
                    
                    # Tentative 2: Fusionner rect_idx et rect_idx+1
                    if rect_idx + 1 < len(corrected_rects):
                        detected_char_next = letter_code_to_hebrew(corrected_codes[rect_idx + 1]) if rect_idx + 1 < len(corrected_codes) else ''
                        detected_chars_i_i1 = detected_char + detected_char_next
                        
                        if debug:
                            logger.debug(f"→ 2ème tentative: Fusion avec FusionCorrection (rect_idx + rect_idx+1 = '{detected_chars_i_i1}')...")
                        
                        result = fusion_correction.try_correct(
                            rect_idx=rect_idx,
                            valid_rects_final=corrected_rects,
                            valid_codes=corrected_codes,
                            expected_char='',  # Pas d'expected_char pour les lettres en trop
                            detected_char=detected_char,
                            detected_chars=detected_chars_i_i1,
                            reference_text=reference_text,
                            detected_text=detected_text_normalized
                        )
                        
                        if result and result.success:
                            if debug:
                                fused_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
                                logger.debug(f"✓ SUCCÈS: Fusion rect_idx + rect_idx+1 réussie -> '{fused_char}'")
                            
                            _apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
                            corrections_applied.append({
                                'type': 'fusion',
                                'position': rect_idx,
                                'fusion_type': 'i_i1',
                                'text': text
                            })
                            diff_changed = True
                            break  # Recalculer le diff
                        elif debug:
                            logger.debug(f"✗ ÉCHEC: Fusion rect_idx + rect_idx+1 n'a pas fonctionné")
                
                # Essayer split simple
                if rect_idx < len(corrected_rects):
                    split_result = try_split(
                        corrected_rects[rect_idx],
                        text[:2] if len(text) >= 2 else text,
                        image,
                        weight_file
                    )
                    
                    if split_result:
                        if debug:
                            char1 = letter_code_to_hebrew(split_result[0]['code'])
                            char2 = letter_code_to_hebrew(split_result[1]['code'])
                            logger.debug(f"→ 2ème tentative: Split simple réussi -> '{char1}' + '{char2}'")
                        
                        corrected_rects[rect_idx] = split_result[0]['rect']
                        corrected_codes[rect_idx] = split_result[0]['code']
                        corrected_rects.insert(rect_idx + 1, split_result[1]['rect'])
                        corrected_codes.insert(rect_idx + 1, split_result[1]['code'])
                        corrections_applied.append({
                            'type': 'split',
                            'position': rect_idx,
                            'text': text
                        })
                        diff_changed = True
                        break  # Recalculer le diff
                
                rect_idx += len(text)
        
        # Si aucune correction n'a été appliquée dans cette itération, on peut sortir
        if not diff_changed:
            break
    
    if iteration >= max_iterations and debug:
        logger.warning(f"Limite de {max_iterations} itérations atteinte")
    
    if debug:
        final_text = ''.join([letter_code_to_hebrew(code) if code != 27 else '' for code in corrected_codes])
        logger.debug(f"Alignement terminé:")
        logger.debug(f"Nombre de corrections appliquées: {len(corrections_applied)}")
        logger.debug(f"Texte final (longueur: {len(final_text)}): {final_text[:100]}...")
    
    return corrected_rects, corrected_codes, corrections_applied


def _apply_correction_result(corrected_rects, corrected_codes, rect_idx, correction_result: CorrectionResult):
    """
    Applique le résultat d'une correction réussie.
    
    Args:
        corrected_rects: Liste des rectangles (modifiée en place)
        corrected_codes: Liste des codes (modifiée en place)
        rect_idx: Index du rectangle à remplacer
        correction_result: CorrectionResult avec les nouveaux rectangles et codes
    """
    # Déterminer l'index du rectangle à remplacer
    replace_idx = correction_result.metadata.get('rect_to_replace_idx', rect_idx)
    
    # Remplacer les rectangles
    for _ in range(correction_result.num_rects_to_replace):
        if replace_idx < len(corrected_rects):
            corrected_rects.pop(replace_idx)
            corrected_codes.pop(replace_idx)
    
    # Insérer les nouveaux rectangles (en ordre inverse pour l'hébreu)
    for j in range(len(correction_result.new_rects) - 1, -1, -1):
        corrected_rects.insert(replace_idx, correction_result.new_rects[j])
        corrected_codes.insert(replace_idx, correction_result.new_codes[j])
def try_split(rect, expected_chars, image, weight_file):
    """
    Essaie de découper un rectangle en deux lettres.
    Hypothèse : 1 rectangle = 2 lettres
    
    Args:
        rect: Rectangle à découper (x, y, w, h)
        expected_chars: Deux caractères attendus (string de 2 caractères)
        image: Image OpenCV
        weight_file: Chemin vers le fichier de poids
        
    Returns:
        list de 2 dicts avec 'rect' et 'code' si la découpe est valide, None sinon
    """
    if len(expected_chars) < 2:
        return None
    
    x, y, w, h = rect
    
    # Découper au milieu horizontalement
    split_x = x + w // 2
    
    # Créer deux rectangles
    rect1 = (x, y, w // 2, h)
    rect2 = (split_x, y, w - w // 2, h)
    
    # Prédire les lettres sur chaque rectangle
    predictions = predict_letters(image, [rect1, rect2], weight_file)
    
    if not predictions or len(predictions) < 2:
        return None
    
    code1, code2 = predictions[0], predictions[1]
    char1 = letter_code_to_hebrew(code1)
    char2 = letter_code_to_hebrew(code2)
    
    # Vérifier si les prédictions correspondent aux caractères attendus
    if char1 == expected_chars[0] and char2 == expected_chars[1]:
        return [
            {'rect': rect1, 'code': code1},
            {'rect': rect2, 'code': code2}
        ]
    
    # Accepter la découpe si les deux prédictions sont valides (pas du bruit)
    if code1 != 27 and code2 != 27:
        return [
            {'rect': rect1, 'code': code1},
            {'rect': rect2, 'code': code2}
        ]
    
    return None


def apply_segmentation_corrections(letter_rects, letter_codes, reference_text, image, weight_file, debug=False):
    """
    Applique les corrections de segmentation en comparant avec le texte de référence.
    
    Args:
        letter_rects: Liste des rectangles détectés
        letter_codes: Liste des codes de lettres détectées
        reference_text: Texte de référence (texte original)
        image: Image OpenCV
        weight_file: Chemin vers le fichier de poids
        debug: Si True, affiche des logs détaillés
        
    Returns:
        tuple: (corrected_rects, corrected_codes, corrections_applied)
    """
    # Convertir les codes en texte
    detected_text = ''.join([letter_code_to_hebrew(code) if code != 27 else '' 
                            for code in letter_codes])
    
    # Aligner le texte
    corrected_rects, corrected_codes, corrections = align_text_with_reference(
        detected_text,
        reference_text,
        letter_rects,
        letter_codes,
        image,
        weight_file,
        debug=debug
    )
    
    return corrected_rects, corrected_codes, corrections
