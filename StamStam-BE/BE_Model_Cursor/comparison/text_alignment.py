"""
Module pour aligner le texte détecté avec le texte original et résoudre les problèmes de segmentation
"""
import diff_match_patch as dmp_module
import cv2
import numpy as np
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.corrections.correction_manager import CorrectionManager
from BE_Model_Cursor.corrections.fusion_correction import FusionCorrection
from BE_Model_Cursor.utils.logger import get_logger
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
from BE_Model_Cursor.utils.contour_detector import _in_same_line


def _get_position_str(corrected_rects, rect_idx):
    """Helper pour obtenir la chaîne de position (text_position ou rect_idx)"""
    if rect_idx < len(corrected_rects) and isinstance(corrected_rects[rect_idx], RectangleWithLine) and corrected_rects[rect_idx].text_position is not None:
        return f"text_pos={corrected_rects[rect_idx].text_position}"
    return f"rect_idx={rect_idx}"


def _get_detected_char(corrected_rects, corrected_codes, rect_idx):
    """Helper pour obtenir la lettre détectée depuis RectangleWithLine ou corrected_codes"""
    if rect_idx < len(corrected_rects) and isinstance(corrected_rects[rect_idx], RectangleWithLine) and corrected_rects[rect_idx].detected_letter:
        return corrected_rects[rect_idx].detected_letter
    elif rect_idx < len(corrected_codes):
        return letter_code_to_hebrew(corrected_codes[rect_idx]) if corrected_codes[rect_idx] != 27 else ''
    return ''


def _get_position(corrected_rects, rect_idx):
    """Helper pour obtenir la position (text_position ou rect_idx)"""
    if rect_idx < len(corrected_rects) and isinstance(corrected_rects[rect_idx], RectangleWithLine) and corrected_rects[rect_idx].text_position is not None:
        return corrected_rects[rect_idx].text_position
    return rect_idx


def _handle_equal_text(corrected_rects, rect_idx, text, diff_idx, debug, logger):
    """Gère le cas où le texte est correct (op == 0)
    
    Returns:
        tuple: (rect_idx, diff_idx)
    """
    if debug:
        pos_str = _get_position_str(corrected_rects, rect_idx)
        logger.debug(f"[Comparaison] Position {pos_str}: ✓ TEXTE CORRECT trouvé: '{text}' (longueur: {len(text)})")
    
    rect_idx += len(text)
    diff_idx += 1
    return rect_idx, diff_idx


def _handle_deleted_text(corrected_rects, corrected_codes, rect_idx, diff, diff_idx, text, correction_manager,
                         reference_text, detected_text_normalized, corrections_applied, debug, logger):
    """Gère le cas où du texte est supprimé dans le détecté (op == -1)
    Peut être soit une substitution, soit une lettre manquante.
    
    Returns:
        tuple: (diff_changed, rect_idx, diff_idx, substitution_processed)
               où substitution_processed indique si on doit ignorer le prochain op == 1
    """
    # Vérifier si c'est une substitution (suivi d'une addition)
    is_substitution = (diff_idx + 1 < len(diff) and diff[diff_idx + 1][0] == 1)
    
    if is_substitution:
        # C'est une substitution : une lettre a été remplacée par une autre
        added_text = diff[diff_idx + 1][1]
        expected_text = text
        diff_changed, rect_idx, diff_idx, substitution_processed = _handle_substitution(
            corrected_rects, corrected_codes, rect_idx, diff, diff_idx, text, added_text, expected_text,
            correction_manager, reference_text, detected_text_normalized, corrections_applied,
            debug, logger
        )
        return diff_changed, rect_idx, diff_idx, substitution_processed
    else:
        # Vraie lettre manquante (pas de rectangle correspondant)
        diff_changed = _handle_missing_letter(
            corrected_rects, corrected_codes, rect_idx, text, correction_manager,
            reference_text, detected_text_normalized, corrections_applied, debug, logger
        )
        diff_idx += 1
        return diff_changed, rect_idx, diff_idx, False


def _handle_added_text(corrected_rects, corrected_codes, rect_idx, text, diff, diff_idx, reference_text,
                       fusion_correction, correction_manager, detected_text_normalized, corrections_applied,
                       image, weight_file, debug, logger):
    """Gère le cas où du texte est ajouté dans le détecté (op == 1) = lettre en trop
    
    Returns:
        tuple: (diff_changed, rect_idx, diff_idx)
    """
    diff_changed, rect_idx, diff_idx = _handle_extra_letter(
        corrected_rects, corrected_codes, rect_idx, text, diff, diff_idx, reference_text,
        fusion_correction, correction_manager, detected_text_normalized, corrections_applied,
        image, weight_file, debug, logger
    )
    return diff_changed, rect_idx, diff_idx


def _handle_substitution_case1(corrected_rects, corrected_codes, rect_idx, expected_char, detected_chars, text, 
                                correction_manager, reference_text, detected_text_normalized, corrections_applied, 
                                debug, logger):
    """CAS 1 de substitution: N rectangles détectés au lieu d'1 lettre attendue"""
    # Vérifier que tous les rectangles à fusionner sont sur la même ligne
    if len(detected_chars) > 1:
        first_rect = corrected_rects[rect_idx]
        all_same_line = True
        
        for i in range(1, len(detected_chars)):
            if rect_idx + i >= len(corrected_rects):
                all_same_line = False
                break
            current_rect = corrected_rects[rect_idx + i]
            
            # Vérifier si les rectangles sont sur la même ligne
            if isinstance(first_rect, RectangleWithLine) and isinstance(current_rect, RectangleWithLine):
                if first_rect.line_number != current_rect.line_number:
                    all_same_line = False
                    break
            else:
                # Calculer la largeur moyenne pour la vérification de compatibilité
                if len(corrected_rects) > 0:
                    avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in corrected_rects) / len(corrected_rects)
                else:
                    avg_width = 50
                if not _in_same_line(first_rect, current_rect, avg_width):
                    all_same_line = False
                    break
        
        if not all_same_line:
            if debug:
                logger.debug(f"→ Fusion de {len(detected_chars)} rectangles SKIPPÉE: les rectangles ne sont pas tous sur la même ligne")
            return False
    
    if debug:
        logger.debug(f"→ 1ère tentative: Fusion de {len(detected_chars)} rectangles pour obtenir '{expected_char}'...")
    
    success = correction_manager.try_and_apply_correction(
        corrected_rects=corrected_rects,
        corrected_codes=corrected_codes,
        rect_idx=rect_idx,
        expected_char=expected_char,
        detected_char=detected_chars[0] if detected_chars else '',
        detected_chars=detected_chars,
        reference_text=reference_text,
        detected_text=detected_text_normalized
    )
    
    if success:
        if debug:
            new_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx)
            logger.debug(f"✓ SUCCÈS: Fusion réussie, '{detected_chars}' -> '{new_char}' (correspond à '{expected_char}')")
        
        position = _get_position(corrected_rects, rect_idx)
        corrections_applied.append({
            'type': 'fusion_correction',
            'position': position,
            'text': text
        })
        return True
    elif debug:
        logger.debug(f"✗ ÉCHEC: Fusion de {len(detected_chars)} rectangles n'a pas donné '{expected_char}'")
    
    return False


def _handle_substitution_case2(corrected_rects, corrected_codes, rect_idx, expected_char, detected_char, text,
                                correction_manager, reference_text, detected_text_normalized, corrections_applied,
                                debug, logger):
    """CAS 2 de substitution: 1 rectangle détecté au lieu d'1 lettre attendue"""
    if debug:
        logger.debug(f"→ 1ère tentative: Correction avec CorrectionManager (extension hauteur ou réunification)...")
    
    # Sauvegarder l'état initial
    saved_rects = corrected_rects[:]
    saved_codes = corrected_codes[:]
    
    success = correction_manager.try_and_apply_correction(
        corrected_rects=corrected_rects,
        corrected_codes=corrected_codes,
        rect_idx=rect_idx,
        expected_char=expected_char,
        detected_char=detected_char,
        reference_text=reference_text,
        detected_text=detected_text_normalized
    )
    
    if success:
        if debug:
            new_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx)
            logger.debug(f"✓ SUCCÈS: Correction réussie, '{detected_char}' -> '{new_char}' (correspond à '{expected_char}')")
        
        position = _get_position(corrected_rects, rect_idx)
        corrections_applied.append({
            'type': 'wrong_letter_correction',
            'position': position,
            'text': text
        })
        return True
    else:
        # Restaurer l'état initial
        corrected_rects[:] = saved_rects
        corrected_codes[:] = saved_codes
        if debug:
            logger.debug(f"✗ ÉCHEC: Correction n'a pas fonctionné")
    
    return False


def _handle_substitution(corrected_rects, corrected_codes, rect_idx, diff, diff_idx, text, added_text, expected_text,
                         correction_manager, reference_text, detected_text_normalized, corrections_applied,
                         debug, logger):
    """Gère une substitution (op == -1 suivi de op == 1)
    
    Returns:
        tuple: (diff_changed, rect_idx, diff_idx, substitution_processed)
    """
    if debug:
        pos_str = _get_position_str(corrected_rects, rect_idx)
        logger.debug(f"[Comparaison] Position {pos_str}: ✗ SUBSTITUTION - détecté '{added_text}' au lieu de '{text}' (longueur attendue: {len(text)}, longueur détectée: {len(added_text)})")
    
    substitution_corrected = False
    
    # CAS 1: N rectangles détectés au lieu d'1 lettre attendue
    if len(added_text) >= 2 and len(expected_text) == 1 and rect_idx + len(added_text) - 1 < len(corrected_rects):
        expected_char = expected_text[0]
        detected_chars = added_text
        if _handle_substitution_case1(corrected_rects, corrected_codes, rect_idx, expected_char, detected_chars, text,
                                       correction_manager, reference_text, detected_text_normalized, corrections_applied,
                                       debug, logger):
            substitution_corrected = True
            return True, rect_idx, diff_idx, False  # diff_changed, rect_idx, diff_idx, substitution_processed
    
    # CAS 2: 1 rectangle détecté au lieu d'1 lettre attendue
    elif len(added_text) == 1 and len(expected_text) == 1 and rect_idx < len(corrected_rects):
        expected_char = expected_text[0]
        detected_char = added_text[0]
        if _handle_substitution_case2(corrected_rects, corrected_codes, rect_idx, expected_char, detected_char, text,
                                      correction_manager, reference_text, detected_text_normalized, corrections_applied,
                                      debug, logger):
            substitution_corrected = True
            return True, rect_idx, diff_idx, False  # diff_changed, rect_idx, diff_idx, substitution_processed
    
    # Si la substitution n'a pas été corrigée, marquer pour ignorer le op == 1 suivant
    if not substitution_corrected:
        rect_idx += len(added_text)
        diff_idx += 1  # Passer l'opération d'addition aussi (le prochain op == 1)
        return False, rect_idx, diff_idx, True  # diff_changed, rect_idx, diff_idx, substitution_processed
    
    return False, rect_idx, diff_idx, False


def _handle_missing_letter(corrected_rects, corrected_codes, rect_idx, text, correction_manager, reference_text,
                           detected_text_normalized, corrections_applied, debug, logger):
    """Gère une lettre manquante (op == -1 sans substitution)"""
    expected_char = text if text else None
    
    if debug:
        pos_str = _get_position_str(corrected_rects, rect_idx)
        logger.debug(f"[Comparaison] Position {pos_str}: ⚠ TEXTE MANQUANT: '{text}' (longueur: {len(text)})")
        if len(text) > 1:
            logger.debug(f"→ Plusieurs lettres manquantes ({len(text)}) → Paracha partielle probable, réunification non applicable")
        else:
            logger.debug(f"→ 1 seule lettre manquante → Tentative de correction avec CorrectionManager (MissingLetterCorrection)...")
    
    success = correction_manager.try_and_apply_correction(
        corrected_rects=corrected_rects,
        corrected_codes=corrected_codes,
        rect_idx=rect_idx,
        expected_char=expected_char,
        detected_char='',
        reference_text=reference_text,
        detected_text=detected_text_normalized
    )
    
    if success:
        if debug:
            new_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx)
            logger.debug(f"✓ SUCCÈS: Lettre manquante trouvée, -> '{new_char}'")
        
        position = _get_position(corrected_rects, rect_idx)
        corrections_applied.append({
            'type': 'missing_letter_correction',
            'position': position,
            'text': text
        })
        return True
    elif debug:
        logger.debug(f"✗ ÉCHEC: Lettre manquante '{expected_char}' non trouvée")
    
    return False


def _try_fusion_with_prev(corrected_rects, corrected_codes, rect_idx, detected_char, expected_char_at_pos,
                          expected_char_at_prev_pos, text, fusion_correction, correction_manager,
                          reference_text, detected_text_normalized, corrections_applied, debug, logger):
    """Tentative 1: Fusionner rect_idx-1 et rect_idx"""
    if rect_idx <= 0:
        return False
    
    # Vérifier que les rectangles sont sur la même ligne
    rect_prev = corrected_rects[rect_idx - 1]
    rect_curr = corrected_rects[rect_idx]
    
    same_line = False
    if isinstance(rect_prev, RectangleWithLine) and isinstance(rect_curr, RectangleWithLine):
        same_line = rect_prev.line_number == rect_curr.line_number
    else:
        # Calculer la largeur moyenne pour la vérification de compatibilité
        if len(corrected_rects) > 0:
            avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in corrected_rects) / len(corrected_rects)
        else:
            avg_width = 50
        same_line = _in_same_line(rect_prev, rect_curr, avg_width)
    
    if not same_line:
        if debug:
            logger.debug(f"→ 1ère tentative SKIPPÉE: rect_idx-1 et rect_idx ne sont pas sur la même ligne")
        return False
    
    prev_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx - 1)
    detected_chars_im1_i = prev_char + detected_char
    
    if debug:
        logger.debug(f"→ 1ère tentative: Fusion avec FusionCorrection (rect_idx-1 + rect_idx = '{detected_chars_im1_i}')...")
        if expected_char_at_pos:
            logger.debug(f"  Lettre attendue après fusion (position actuelle): '{expected_char_at_pos}'")
        if expected_char_at_prev_pos:
            logger.debug(f"  Lettre attendue à la position précédente: '{expected_char_at_prev_pos}'")
    
    result = fusion_correction.try_correct(
        rect_idx=rect_idx - 1,
        valid_rects_final=corrected_rects,
        valid_codes=corrected_codes,
        expected_char='',
        detected_char=detected_char,
        detected_chars=detected_chars_im1_i,
        reference_text=reference_text,
        detected_text=detected_text_normalized
    )
    
    if result and result.success:
        fused_char = letter_code_to_hebrew(result.new_codes[0]) if result.new_codes else None
        
        # Cas 1: La fusion donne la lettre attendue à la position actuelle
        if expected_char_at_pos and fused_char == expected_char_at_pos:
            if debug:
                logger.debug(f"✓ SUCCÈS: Fusion rect_idx-1 + rect_idx réussie -> '{fused_char}' (correspond à '{expected_char_at_pos}' à la position actuelle)")
            
            correction_manager._apply_correction_result(corrected_rects, corrected_codes, rect_idx - 1, result)
            position = _get_position(corrected_rects, rect_idx - 1)
            corrections_applied.append({
                'type': 'fusion',
                'position': position,
                'fusion_type': 'im1_i',
                'text': text
            })
            return True
        
        # Cas 2: La fusion donne la lettre attendue à la position précédente
        elif expected_char_at_prev_pos and fused_char == expected_char_at_prev_pos:
            if debug:
                logger.debug(f"✓ SUCCÈS: Fusion rect_idx-1 + rect_idx réussie -> '{fused_char}' (correspond à la lettre attendue à la position précédente '{expected_char_at_prev_pos}')")
            
            correction_manager._apply_correction_result(corrected_rects, corrected_codes, rect_idx - 1, result)
            position = _get_position(corrected_rects, rect_idx - 1)
            corrections_applied.append({
                'type': 'fusion',
                'position': position,
                'fusion_type': 'im1_i',
                'text': text
            })
            return True
        elif debug:
            logger.debug(f"✗ ÉCHEC: Fusion donne '{fused_char}' mais ne correspond ni à '{expected_char_at_pos}' (position actuelle) ni à '{expected_char_at_prev_pos}' (position précédente)")
    elif debug:
        logger.debug(f"✗ ÉCHEC: Fusion rect_idx-1 + rect_idx n'a pas fonctionné")
    
    return False


def _try_fusion_with_next(corrected_rects, corrected_codes, rect_idx, detected_char, expected_char_at_pos, text,
                          fusion_correction, correction_manager, reference_text, detected_text_normalized,
                          corrections_applied, debug, logger):
    """Tentative 2: Fusionner rect_idx et rect_idx+1"""
    if rect_idx + 1 >= len(corrected_rects):
        return False
    
    # Vérifier que les rectangles sont sur la même ligne
    rect_curr = corrected_rects[rect_idx]
    rect_next = corrected_rects[rect_idx + 1]
    
    same_line = False
    if isinstance(rect_curr, RectangleWithLine) and isinstance(rect_next, RectangleWithLine):
        same_line = rect_curr.line_number == rect_next.line_number
    else:
        # Calculer la largeur moyenne pour la vérification de compatibilité
        if len(corrected_rects) > 0:
            avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in corrected_rects) / len(corrected_rects)
        else:
            avg_width = 50
        same_line = _in_same_line(rect_curr, rect_next, avg_width)
    
    if not same_line:
        if debug:
            logger.debug(f"→ 2ème tentative SKIPPÉE: rect_idx et rect_idx+1 ne sont pas sur la même ligne")
        return False
    
    next_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx + 1)
    detected_chars_i_i1 = detected_char + next_char
    
    if debug:
        logger.debug(f"→ 2ème tentative: Fusion avec FusionCorrection (rect_idx + rect_idx+1 = '{detected_chars_i_i1}')...")
        if expected_char_at_pos:
            logger.debug(f"  Lettre attendue après fusion: '{expected_char_at_pos}'")
    
    result = fusion_correction.try_correct(
        rect_idx=rect_idx,
        valid_rects_final=corrected_rects,
        valid_codes=corrected_codes,
        expected_char=expected_char_at_pos,
        detected_char=detected_char,
        detected_chars=detected_chars_i_i1,
        reference_text=reference_text,
        detected_text=detected_text_normalized
    )
    
    if result and result.success:
        if debug:
            fused_char = None
            if result.new_rects and len(result.new_rects) > 0:
                if isinstance(result.new_rects[0], RectangleWithLine) and result.new_rects[0].detected_letter:
                    fused_char = result.new_rects[0].detected_letter
                elif result.new_codes:
                    fused_char = letter_code_to_hebrew(result.new_codes[0])
            logger.debug(f"✓ SUCCÈS: Fusion rect_idx + rect_idx+1 réussie -> '{fused_char}' (correspond à '{expected_char_at_pos}')")
        
        correction_manager._apply_correction_result(corrected_rects, corrected_codes, rect_idx, result)
        position = _get_position(corrected_rects, rect_idx)
        corrections_applied.append({
            'type': 'fusion',
            'position': position,
            'fusion_type': 'i_i1',
            'text': text
        })
        return True
    elif debug:
        logger.debug(f"✗ ÉCHEC: Fusion rect_idx + rect_idx+1 n'a pas fonctionné")
    
    return False


def _try_split_extra_letter(corrected_rects, corrected_codes, rect_idx, text, image, weight_file, corrections_applied,
                            debug, logger):
    """Essaie de diviser un rectangle en deux pour une lettre en trop"""
    if rect_idx >= len(corrected_rects):
        return False
    
    split_result = try_split(
        corrected_rects[rect_idx],
        text[:2] if len(text) >= 2 else text,
        image,
        weight_file
    )
    
    if not split_result:
        return False
    
    # Conserver line_number du rectangle original
    original_rect = corrected_rects[rect_idx]
    line_number = original_rect.line_number if isinstance(original_rect, RectangleWithLine) else 0
    
    # Créer les nouveaux RectangleWithLine
    rect1 = split_result[0]['rect']
    code1 = split_result[0]['code']
    detected_letter1 = letter_code_to_hebrew(code1) if code1 != 27 else None
    if isinstance(rect1, RectangleWithLine):
        rect1.detected_letter = detected_letter1
        rect1.line_number = line_number
    else:
        rect1 = RectangleWithLine(rect1[0], rect1[1], rect1[2], rect1[3], line_number, detected_letter1, None, (0, 255, 0))
    
    rect2 = split_result[1]['rect']
    code2 = split_result[1]['code']
    detected_letter2 = letter_code_to_hebrew(code2) if code2 != 27 else None
    if isinstance(rect2, RectangleWithLine):
        rect2.detected_letter = detected_letter2
        rect2.line_number = line_number
        rect2.color = (0, 255, 0)
    else:
        rect2 = RectangleWithLine(rect2[0], rect2[1], rect2[2], rect2[3], line_number, detected_letter2, None, (0, 255, 0))
    
    if debug:
        logger.debug(f"→ 2ème tentative: Split simple réussi -> '{detected_letter1}' + '{detected_letter2}'")
    
    corrected_rects[rect_idx] = rect1
    corrected_codes[rect_idx] = code1
    corrected_rects.insert(rect_idx + 1, rect2)
    corrected_codes.insert(rect_idx + 1, code2)
    
    # Réindexer tous les rectangles pour maintenir text_position cohérent
    for i, rect in enumerate(corrected_rects):
        if isinstance(rect, RectangleWithLine):
            rect.text_position = i
    
    position = _get_position(corrected_rects, rect_idx)
    corrections_applied.append({
        'type': 'split',
        'position': position,
        'text': text
    })
    return True


def _handle_extra_letter(corrected_rects, corrected_codes, rect_idx, text, diff, diff_idx, reference_text,
                         fusion_correction, correction_manager, detected_text_normalized, corrections_applied,
                         image, weight_file, debug, logger):
    """Gère une lettre en trop (op == 1)"""
    if debug:
        pos_str = _get_position_str(corrected_rects, rect_idx)
        logger.debug(f"[Comparaison] Position {pos_str}: + TEXTE EN TROP: '{text}' (longueur: {len(text)})")
    
    # Déterminer la lettre attendue à cette position dans le texte de référence
    ref_pos = sum(len(diff[j][1]) for j in range(diff_idx) if diff[j][0] == 0 or diff[j][0] == -1)
    expected_char_at_pos = ''
    if ref_pos < len(reference_text):
        expected_char_at_pos = reference_text[ref_pos]
        if debug:
            logger.debug(f"[Comparaison] Lettre attendue à cette position dans la référence: '{expected_char_at_pos}'")
    
    # Déterminer aussi la lettre attendue à la position précédente
    expected_char_at_prev_pos = ''
    if ref_pos > 0:
        expected_char_at_prev_pos = reference_text[ref_pos - 1]
        if debug:
            logger.debug(f"[Comparaison] Lettre attendue à la position précédente dans la référence: '{expected_char_at_prev_pos}'")
    
    # Essayer fusion simple avec FusionCorrection
    if rect_idx > 0 and rect_idx < len(corrected_rects):
        detected_char = _get_detected_char(corrected_rects, corrected_codes, rect_idx)
        
        # Tentative 1: Fusionner rect_idx-1 et rect_idx
        if _try_fusion_with_prev(corrected_rects, corrected_codes, rect_idx, detected_char, expected_char_at_pos,
                                expected_char_at_prev_pos, text, fusion_correction, correction_manager,
                                reference_text, detected_text_normalized, corrections_applied, debug, logger):
            return True, rect_idx, diff_idx
        
        # Tentative 2: Fusionner rect_idx et rect_idx+1
        if _try_fusion_with_next(corrected_rects, corrected_codes, rect_idx, detected_char, expected_char_at_pos, text,
                                fusion_correction, correction_manager, reference_text, detected_text_normalized,
                                corrections_applied, debug, logger):
            return True, rect_idx, diff_idx
    
    # Essayer split simple
    if _try_split_extra_letter(corrected_rects, corrected_codes, rect_idx, text, image, weight_file, corrections_applied,
                               debug, logger):
        return True, rect_idx, diff_idx
    
    rect_idx += len(text)
    diff_idx += 1
    return False, rect_idx, diff_idx


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
        # Utiliser detected_letter depuis RectangleWithLine si disponible
        detected_text_normalized = ''
        for i, rect in enumerate(corrected_rects):
            if isinstance(rect, RectangleWithLine) and rect.detected_letter:
                detected_text_normalized += rect.detected_letter
            elif i < len(corrected_codes):
                # Fallback : utiliser le code si detected_letter n'est pas disponible
                detected_text_normalized += letter_code_to_hebrew(corrected_codes[i]) if corrected_codes[i] != 27 else ''
        diff = dmp.diff_main(reference_text, detected_text_normalized)
        dmp.diff_cleanupSemantic(diff)
        
        if debug and iteration == 1:
            logger.debug(f"Diff initial calculé avec {len(diff)} opérations")
        elif debug and iteration > 1:
            logger.debug(f"Itération {iteration}: Diff recalculé avec {len(diff)} opérations après correction")
        
        # Parcourir les différences pour identifier les problèmes
        rect_idx = 0
        diff_changed = False
        
        # Variable pour suivre si on a traité une substitution (pour éviter de traiter le op == 1 suivant comme "lettre en trop")
        substitution_processed = False
        
        diff_idx = 0
        while diff_idx < len(diff):
            op, text = diff[diff_idx]
            
            # Si on a traité une substitution qui a échoué, ignorer le op == 1 suivant
            if substitution_processed and op == 1:
                if debug:
                    pos_str = _get_position_str(corrected_rects, rect_idx)
                    logger.debug(f"[Comparaison] Position {pos_str}: Ignorer op==1 (ajout) car c'est la partie ajoutée d'une substitution non corrigée")
                rect_idx += len(text)
                substitution_processed = False
                diff_idx += 1
                continue
            
            if op == 0:  # Égalité - texte correct
                rect_idx, diff_idx = _handle_equal_text(corrected_rects, rect_idx, text, diff_idx, debug, logger)
                
            elif op == -1:  # Supprimé dans détecté = lettre manquante ou substitution
                diff_changed, rect_idx, diff_idx, substitution_processed = _handle_deleted_text(
                    corrected_rects, corrected_codes, rect_idx, diff, diff_idx, text, correction_manager,
                    reference_text, detected_text_normalized, corrections_applied, debug, logger
                )
                if diff_changed:
                    break
                if substitution_processed:
                    continue
                
            elif op == 1:  # Ajouté dans détecté = lettre en trop
                diff_changed, rect_idx, diff_idx = _handle_added_text(
                    corrected_rects, corrected_codes, rect_idx, text, diff, diff_idx, reference_text,
                    fusion_correction, correction_manager, detected_text_normalized, corrections_applied,
                    image, weight_file, debug, logger
                )
                if diff_changed:
                    break
        
        # Si aucune correction n'a été appliquée dans cette itération, on peut sortir
        if not diff_changed:
            break
    
    if iteration >= max_iterations and debug:
        logger.warning(f"Limite de {max_iterations} itérations atteinte")
    
    if debug:
        # Utiliser detected_letter depuis RectangleWithLine si disponible
        final_text = ''
        for i, rect in enumerate(corrected_rects):
            if isinstance(rect, RectangleWithLine) and rect.detected_letter:
                final_text += rect.detected_letter
            elif i < len(corrected_codes):
                # Fallback : utiliser le code si detected_letter n'est pas disponible
                final_text += letter_code_to_hebrew(corrected_codes[i]) if corrected_codes[i] != 27 else ''
        logger.debug(f"Alignement terminé:")
        logger.debug(f"Nombre de corrections appliquées: {len(corrections_applied)}")
        logger.debug(f"Texte final (longueur: {len(final_text)}): {final_text[:100]}...")
    
    return corrected_rects, corrected_codes, corrections_applied


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
    
    # Vérifier que le rectangle est valide et assez large pour être divisé
    if w < 10 or h < 5:  # Minimum pour pouvoir diviser
        return None
    
    # Vérifier que le rectangle est dans les limites de l'image
    if x < 0 or y < 0 or x + w > image.shape[1] or y + h > image.shape[0]:
        return None
    
    # Découper au milieu horizontalement
    split_x = x + w // 2
    
    # Créer deux rectangles avec validation
    w1 = w // 2
    w2 = w - w // 2
    
    # S'assurer que chaque rectangle a une largeur minimale
    if w1 < 5 or w2 < 5:
        return None
    
    rect1 = (x, y, w1, h)
    rect2 = (split_x, y, w2, h)
    
    # Vérifier que les rectangles sont dans les limites de l'image
    if (rect1[0] + rect1[2] > image.shape[1] or rect1[1] + rect1[3] > image.shape[0] or
        rect2[0] + rect2[2] > image.shape[1] or rect2[1] + rect2[3] > image.shape[0]):
        return None
    
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
