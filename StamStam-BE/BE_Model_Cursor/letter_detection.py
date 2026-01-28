"""
Module de détection de lettres hébraïques dans une image de paracha.
Ce module est indépendant du reste du code existant mais utilise les mêmes principes.
"""
import cv2
import numpy as np
import base64
import os
import sys

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

from BE_Model_Cursor.utils.contour_detector import detect_and_order_contours, detect_contours, _in_same_line, _show_rectangles_interactive
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.comparison.paracha_matcher import detect_paracha, load_paracha_texts
from BE_Model_Cursor.comparison.text_alignment import apply_segmentation_corrections
from BE_Model_Cursor.comparison.space_comparator import SpaceComparator
from BE_Model_Cursor.utils.logger import get_logger
from BE_Model_Cursor.utils.margin_filter import filter_margin_noise
import diff_match_patch as dmp_module


def crop_parchment(image):
    """
    Détecte et recadre la zone du parchemin dans l'image.
    Utilise la détection de contours pour trouver la zone principale du texte.
    """
    # Convertir en niveaux de gris
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Appliquer un flou gaussien
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Seuillage adaptatif
    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2
    )
    
    # Trouver les contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Trouver le plus grand contour (probablement le parchemin)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Obtenir le rectangle englobant
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Ajouter une marge
    margin = 20
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(image.shape[1] - x, w + 2 * margin)
    h = min(image.shape[0] - y, h + 2 * margin)
    
    # Recadrer l'image
    cropped = image[y:y+h, x:x+w]
    
    # Si la zone recadrée est trop petite, retourner l'image originale
    if cropped.shape[0] < 100 or cropped.shape[1] < 100:
        return image
    
    return cropped


def redetect_rectangles_in_rect(image, rect, min_contour_area=30):
    """
    Re-détecte les rectangles dans une région spécifique de l'image.
    Utilisé pour vérifier si un rectangle unifié contient en fait 2 lettres.
    N'applique PAS la combinaison des chevauchements.
    """
    x, y, w, h = rect
    
    # Extraire la région de l'image
    x = max(0, int(x))
    y = max(0, int(y))
    w = min(image.shape[1] - x, int(w))
    h = min(image.shape[0] - y, int(h))
    
    if w <= 0 or h <= 0:
        return []
    
    region = image[y:y+h, x:x+w]
    
    if region.size == 0:
        return []
    
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
    
    valid_rects = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_contour_area:
            continue
        
        rx, ry, rw, rh = cv2.boundingRect(contour)
        
        if rw > 5 and rh > 8 and rw < 1000:
            aspect_ratio = rw / rh if rh > 0 else 0
            if 0.1 < aspect_ratio < 5.0:
                valid_rects.append((rx, ry, rw, rh))
    
    valid_rects.sort(key=lambda r: r[0] + r[2], reverse=True)
    
    absolute_rects = []
    for rx, ry, rw, rh in valid_rects:
        abs_x = x + rx
        abs_y = y + ry
        absolute_rects.append((abs_x, abs_y, rw, rh))
    
    return absolute_rects


def detect_letters(image, weight_file=None, overflow_dir=None, debug=False):
    """
    Détecte les lettres hébraïques dans une image, les ordonne, les identifie avec le modèle ML,
    compare avec les parachot et retourne l'image avec les rectangles ET le nom de la paracha.
    """
    backend_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if weight_file is None:
        try:
            from config import config as app_config
            weight_file = app_config.MODEL_PATH
        except ImportError:
         weight_file = os.path.join(backend_dir_path, 'ocr', 'model', 'output', 'Nadam_beta_1_256_30.hdf5')
    
    if overflow_dir is None:
        try:
            from config import config as app_config
            overflow_dir = app_config.OVERFLOW_DIR
        except ImportError:
            overflow_dir = os.path.join(backend_dir_path, 'overflow')
    
    logger = get_logger(__name__, debug=debug)
    
    ordered_rects = detect_and_order_contours(image, min_contour_area=50)
    
    if len(ordered_rects) == 0:
        logger.warning("Aucune lettre détectée dans l'image")
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre détectée", "", []
    
    if debug:
        logger.debug(f"Prédiction des lettres avec le modèle ML...")
        logger.debug(f"Nombre de rectangles à prédire: {len(ordered_rects)}")
    letter_codes = predict_letters(image, ordered_rects, weight_file)
    if debug:
        logger.debug(f"Prédiction terminée: {len(letter_codes)} codes obtenus")
        
        predicted_labels = []
        for code in letter_codes:
            if code == 27:
                predicted_labels.append("?")
            else:
                predicted_labels.append(letter_code_to_hebrew(code))
        
        try:
            _show_rectangles_interactive(
                image, 
                ordered_rects, 
                "Lettres Detectees", 
                "Lettres Detectees (apres prediction)", 
                color=(255, 0, 0),  # Bleu
                labels=predicted_labels
            )
        except Exception as e:
            logger.warning(f"Impossible d'afficher les lettres interactivement: {e}")
    
    for rect, code in zip(ordered_rects, letter_codes):
        if isinstance(rect, RectangleWithLine):
            rect.detected_letter = letter_code_to_hebrew(code) if code != 27 else None
    
    valid_letter_data = [(rect, code) for rect, code in zip(ordered_rects, letter_codes) if code != 27]
    invalid_count = len(ordered_rects) - len(valid_letter_data)
    if invalid_count > 0:
        logger.debug(f"{invalid_count} rectangles filtrés (code 27 = zevel/noise)")
    
    if len(valid_letter_data) == 0:
        logger.error("Aucune lettre valide détectée après filtrage")
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre valide détectée", "", []
    
    valid_rects_final, valid_codes = zip(*valid_letter_data)
    valid_rects_final = list(valid_rects_final)
    valid_codes = list(valid_codes)
    
    # Filtrer le bruit dans les marges (lettres isolées)
    if debug:
        logger.debug("Filtrage du bruit dans les marges...")
    valid_rects_final, valid_codes = filter_margin_noise(valid_rects_final, valid_codes, image.shape, logger)
    
    for i, rect in enumerate(valid_rects_final):
        if isinstance(rect, RectangleWithLine):
            rect.text_position = i
    
    if debug:
        logger.debug(f"{len(valid_rects_final)} lettres valides conservées")
    
    if debug:
        logger.debug(f"Détection de la paracha...")
    paracha_name, detected_text = detect_paracha(list(valid_codes), overflow_dir)
    
    reference_text = ''
    
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        paracha_texts = load_paracha_texts(overflow_dir)
        reference_text = paracha_texts.get(paracha_name, '')
        
        if reference_text:
            # Pour l'alignement et les corrections, on utilise une version sans espaces
            reference_text_clean = reference_text.replace(' ', '')
            
            if debug:
                logger.debug(f"Application des corrections de segmentation pour {paracha_name}")
            
            corrected_rects, corrected_codes, corrections = apply_segmentation_corrections(
                valid_rects_final,
                valid_codes,
                reference_text_clean,
                image,
                weight_file,
                debug=debug
            )
            
            valid_rects_final = corrected_rects
            valid_codes = corrected_codes
            
            # Construire le texte détecté SANS espaces d'abord
            detected_text_without_spaces = ''
            for i, rect in enumerate(valid_rects_final):
                letter = ''
                if isinstance(rect, RectangleWithLine) and rect.detected_letter:
                    letter = rect.detected_letter
                elif i < len(valid_codes):
                    letter = letter_code_to_hebrew(valid_codes[i]) if valid_codes[i] != 27 else ''
                detected_text_without_spaces += letter
            
            # Calculer la largeur moyenne
            if len(valid_rects_final) > 0:
                avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in valid_rects_final) / len(valid_rects_final)
            else:
                avg_width = 50
            
            if debug:
                logger.debug(f"Détection espaces: Width moyenne={avg_width:.1f}")
                logger.debug("=== UTILISATION DU NOUVEAU COMPARATEUR D'ESPACES ===")
            
            # Utiliser le nouveau comparateur d'espaces
            space_comparator = SpaceComparator(debug=debug)
            detected_text, space_stats = space_comparator.compare_and_correct_spaces(
                reference_text=reference_text,
                detected_text_without_spaces=detected_text_without_spaces,
                letter_rects=valid_rects_final,
                avg_width=avg_width,
                space_threshold_ratio=0.45,
                image=image  # Passer l'image pour le raffinement des rectangles
            )
            
            if debug:
                logger.debug(f"Texte détecté final (avec espaces corrigés): {detected_text}")
                logger.debug(f"Statistiques espaces (SpaceComparator): {space_stats}")
            
            # ========== LOGS DÉTAILLÉS COMPARAISON ESPACES ==========
            logger.info("=" * 80)
            logger.info("=== COMPARAISON DÉTAILLÉE DES ESPACES (NOUVEAU ALGORITHME) ===")
            logger.info("=" * 80)
            logger.info(f"Espaces géométriques détectés: {space_stats['geometric_spaces']}")
            logger.info(f"Espaces attendus (référence): {space_stats['expected_spaces']}")
            logger.info(f"Espaces finaux: {space_stats['final_spaces']}")
            logger.info(f"Résultats: Correct={space_stats['correct']}, Manquant={space_stats['missing']}, En trop={space_stats['extra']}")
            logger.info(f"Précision: {space_stats['precision']:.1f}%")
            logger.info("=" * 80)
            
            # ========== LOGS DÉTAILLÉS COMPARAISON ESPACES (ANCIEN FORMAT) ==========
            logger.info("=" * 80)
            logger.info("=== COMPARAISON DÉTAILLÉE DES ESPACES ===")
            logger.info("=" * 80)
            
            # Extraire les positions des espaces dans le texte détecté
            detected_spaces = []
            for pos, char in enumerate(detected_text):
                if char == ' ':
                    detected_spaces.append(pos)
            
            # Extraire les positions des espaces dans le texte de référence
            reference_spaces = []
            for pos, char in enumerate(reference_text):
                if char == ' ':
                    reference_spaces.append(pos)
            
            logger.info(f"ESPACES DÉTECTÉS: {len(detected_spaces)} espaces aux positions: {detected_spaces}")
            logger.info(f"ESPACES RÉFÉRENCE: {len(reference_spaces)} espaces aux positions: {reference_spaces}")
            
            # Créer des représentations avec marqueurs d'espaces pour visualisation
            def mark_spaces(text, space_positions):
                """Marque les espaces dans le texte pour le log"""
                result = []
                for i, char in enumerate(text):
                    if i in space_positions:
                        result.append('_')
                    else:
                        result.append(char)
                return ''.join(result)
            
            # Afficher les textes avec marqueurs d'espaces (premiers 200 caractères)
            max_display = 200
            ref_display = reference_text[:max_display] if len(reference_text) <= max_display else reference_text[:max_display] + "..."
            det_display = detected_text[:max_display] if len(detected_text) <= max_display else detected_text[:max_display] + "..."
            
            ref_marked = mark_spaces(ref_display, [p for p in reference_spaces if p < max_display])
            det_marked = mark_spaces(det_display, [p for p in detected_spaces if p < max_display])
            
            logger.info(f"RÉFÉRENCE (premiers {min(max_display, len(reference_text))} chars): {ref_marked}")
            logger.info(f"DÉTECTÉ (premiers {min(max_display, len(detected_text))} chars): {det_marked}")
            
            # Comparaison détaillée : espaces corrects, manquants, en trop
            # On compare en alignant les lettres (sans espaces) pour trouver les correspondances
            ref_chars_only = reference_text.replace(' ', '')
            det_chars_only = detected_text.replace(' ', '')
            
            # Utiliser diff_match_patch pour aligner les lettres
            dmp_temp = dmp_module.diff_match_patch()
            char_diff = dmp_temp.diff_main(ref_chars_only, det_chars_only)
            dmp_temp.diff_cleanupSemantic(char_diff)
            
            # Reconstruire les positions d'espaces dans les versions sans espaces
            # En parcourant le diff, on peut mapper les positions d'espaces
            ref_char_to_space_map = {}  # position dans ref_chars_only -> position dans reference_text
            det_char_to_space_map = {}  # position dans det_chars_only -> position dans detected_text
            
            ref_char_pos = 0
            for i, char in enumerate(reference_text):
                if char != ' ':
                    ref_char_to_space_map[ref_char_pos] = i
                    ref_char_pos += 1
            
            det_char_pos = 0
            for i, char in enumerate(detected_text):
                if char != ' ':
                    det_char_to_space_map[det_char_pos] = i
                    det_char_pos += 1
            
            # Analyser les espaces par rapport à l'alignement des lettres
            correct_spaces = []
            missing_spaces = []
            extra_spaces = []
            
            # Parcourir le texte de référence et vérifier chaque espace
            ref_char_idx = 0
            for ref_space_pos in reference_spaces:
                # Trouver la position de la lettre avant cet espace dans ref_chars_only
                # L'espace est après la lettre à la position ref_space_pos - 1 dans reference_text
                if ref_space_pos > 0:
                    # Trouver combien de lettres non-espaces il y a avant ref_space_pos
                    letters_before = sum(1 for i in range(ref_space_pos) if reference_text[i] != ' ')
                    if letters_before > 0:
                        ref_char_before_space = letters_before - 1
                        # Vérifier si dans detected_text, il y a un espace après la lettre correspondante
                        if ref_char_before_space in det_char_to_space_map:
                            det_char_pos = det_char_to_space_map[ref_char_before_space]
                            # L'espace devrait être à det_char_pos + 1 dans detected_text
                            if det_char_pos + 1 < len(detected_text) and detected_text[det_char_pos + 1] == ' ':
                                correct_spaces.append((ref_space_pos, det_char_pos + 1))
                            else:
                                missing_spaces.append(ref_space_pos)
                        else:
                            missing_spaces.append(ref_space_pos)
                    else:
                        missing_spaces.append(ref_space_pos)
                else:
                    missing_spaces.append(ref_space_pos)
            
            # Parcourir le texte détecté et trouver les espaces en trop
            det_char_idx = 0
            for det_space_pos in detected_spaces:
                # Vérifier si cet espace correspond à un espace dans la référence
                is_correct = False
                for (ref_pos, det_pos) in correct_spaces:
                    if det_pos == det_space_pos:
                        is_correct = True
                        break
                if not is_correct:
                    extra_spaces.append(det_space_pos)
            
            logger.info("")
            logger.info("--- RÉSULTATS COMPARAISON ESPACES ---")
            logger.info(f"ESPACES CORRECTS: {len(correct_spaces)}")
            for ref_pos, det_pos in correct_spaces[:10]:  # Limiter à 10 pour ne pas surcharger
                ref_context = reference_text[max(0, ref_pos-5):min(len(reference_text), ref_pos+5)]
                det_context = detected_text[max(0, det_pos-5):min(len(detected_text), det_pos+5)]
                logger.info(f"  ✓ Ref[{ref_pos}]: '{ref_context}' <-> Det[{det_pos}]: '{det_context}'")
            if len(correct_spaces) > 10:
                logger.info(f"  ... et {len(correct_spaces) - 10} autres espaces corrects")
            
            logger.info(f"ESPACES MANQUANTS: {len(missing_spaces)}")
            for ref_pos in missing_spaces[:10]:
                context = reference_text[max(0, ref_pos-5):min(len(reference_text), ref_pos+5)]
                logger.info(f"  ✗ Manquant à Ref[{ref_pos}]: '{context}'")
            if len(missing_spaces) > 10:
                logger.info(f"  ... et {len(missing_spaces) - 10} autres espaces manquants")
            
            logger.info(f"ESPACES EN TROP: {len(extra_spaces)}")
            for det_pos in extra_spaces[:10]:
                context = detected_text[max(0, det_pos-5):min(len(detected_text), det_pos+5)]
                logger.info(f"  + En trop à Det[{det_pos}]: '{context}'")
            if len(extra_spaces) > 10:
                logger.info(f"  ... et {len(extra_spaces) - 10} autres espaces en trop")
            
            logger.info("")
            logger.info(f"STATISTIQUES: Correct={len(correct_spaces)}, Manquant={len(missing_spaces)}, En trop={len(extra_spaces)}")
            logger.info(f"PRÉCISION ESPACES: {len(correct_spaces) / len(reference_spaces) * 100:.1f}%" if len(reference_spaces) > 0 else "PRÉCISION ESPACES: N/A (aucun espace de référence)")
            logger.info("=" * 80)
            # ========== FIN LOGS DÉTAILLÉS COMPARAISON ESPACES ==========
            
            # Mettre à jour les couleurs des rectangles en fonction des différences (avec espaces)
            dmp = dmp_module.diff_match_patch()
            diff = dmp.diff_main(reference_text, detected_text)
            dmp.diff_cleanupSemantic(diff)
            
            rect_idx = 0
            i = 0
            
            while i < len(diff):
                op, text = diff[i]
                
                if op == 0:  # Égalité
                    for char in text:
                        if char == ' ':
                            continue
                        if rect_idx < len(valid_rects_final):
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                valid_rects_final[rect_idx].color = (0, 255, 0)  # Vert
                            rect_idx += 1
                    i += 1
                
                elif op == -1:  # Manquant (dans detected)
                    if i + 1 < len(diff) and diff[i + 1][0] == 1:
                        # Substitution
                        added_text = diff[i + 1][1]
                        for char in added_text:
                            if char == ' ':
                                continue
                            if rect_idx < len(valid_rects_final):
                                if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                    valid_rects_final[rect_idx].color = (0, 165, 255)  # Orange
                                rect_idx += 1
                        i += 2
                    else:
                        # Vrai manquant : pas de rectangle à colorer
                        i += 1
                
                elif op == 1:  # En trop (dans detected)
                    for char in text:
                        if char == ' ':
                            continue
                        if rect_idx < len(valid_rects_final):
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                valid_rects_final[rect_idx].color = (255, 0, 0)  # Bleu
                            rect_idx += 1
                    i += 1
    
    # Créer une copie de l'image originale pour dessiner les rectangles
    result_image = image.copy()
    
    # Calculer les différences et dessiner avec des couleurs différentes
    differences_info = []
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        if reference_text:
            dmp = dmp_module.diff_match_patch()
            diff = dmp.diff_main(reference_text, detected_text)
            dmp.diff_cleanupSemantic(diff)
            
            if debug:
                logger.debug(f"Comparaison finale (avec espaces):")
                logger.debug(f"  Ref: {reference_text[:50]}...")
                logger.debug(f"  Det: {detected_text[:50]}...")
            
            rect_idx = 0
            i = 0
            current_det_pos = 0
            
            # Calculer la largeur moyenne une fois au début
            if len(valid_rects_final) > 0:
                avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in valid_rects_final) / len(valid_rects_final)
            else:
                avg_width = 50
            
            while i < len(diff):
                op, text = diff[i]
                
                if op == 0:  # Égalité
                    for char in text:
                        if char == ' ':
                            current_det_pos += 1
                            continue
                        
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            color = (0, 255, 0)
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine) and valid_rects_final[rect_idx].color:
                                color = valid_rects_final[rect_idx].color
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                            rect_idx += 1
                        current_det_pos += 1
                    i += 1
                
                elif op == -1:  # Manquant
                    if i + 1 < len(diff) and diff[i + 1][0] == 1:
                        # Substitution
                        added_text = diff[i + 1][1]
                        expected_text = text
                        
                        # Contexte (avec espaces car detected_text a des espaces)
                        start_idx = max(0, current_det_pos - 10)
                        context_before = detected_text[start_idx:current_det_pos]
                        end_idx = min(len(detected_text), current_det_pos + len(added_text) + 10)
                        context_after = detected_text[current_det_pos + len(added_text):end_idx]
                        
                        for char_idx, char in enumerate(added_text):
                            if char == ' ':
                                # Espace en trop dans le détecté (manque dans la référence)
                                # Créer une erreur d'espace manquant
                                if rect_idx > 0 and rect_idx <= len(valid_rects_final):
                                    # Positionner le marqueur entre les lettres
                                    if rect_idx > 0:
                                        x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                                        if rect_idx < len(valid_rects_final):
                                            x2, y2, w2, h2 = valid_rects_final[rect_idx]
                                            marker_x = (x1 + w1 + x2) // 2
                                            marker_y = min(y1, y2) + max(h1, h2) // 2
                                            marker_w = 20
                                            marker_h = max(h1, h2)
                                            marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                                        else:
                                            spacing = max(20, int(avg_width * 0.5))
                                            marker_x = max(0, x1 - spacing)
                                            marker_position = (marker_x, y1, 20, h1)
                                    else:
                                        marker_position = (10, 10, 20, 30)
                                    
                                    differences_info.append({
                                        'type': 'missing',
                                        'text': ' ',  # Espace manquant
                                        'position': rect_idx,
                                        'context_before': context_before,
                                        'context_after': context_after,
                                        'marker_position': marker_position
                                    })
                                current_det_pos += 1
                                continue
                            
                            if rect_idx < len(valid_rects_final):
                                x, y, w, h = valid_rects_final[rect_idx]
                                color = (0, 165, 255)
                                if isinstance(valid_rects_final[rect_idx], RectangleWithLine) and valid_rects_final[rect_idx].color:
                                    color = valid_rects_final[rect_idx].color
                                cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                                
                                exp_char = expected_text[char_idx] if char_idx < len(expected_text) else ''
                                differences_info.append({
                                    'type': 'wrong',
                                    'text': char,
                                    'expected': exp_char,
                                    'position': rect_idx,
                                    'rect': (x, y, w, h),
                                    'context_before': context_before,
                                    'context_after': context_after
                                })
                                rect_idx += 1
                            current_det_pos += 1
                        i += 2
                    else:
                        # Vrai manquant (lettre ou espace)
                        # Contexte (sur detected_text)
                        start_idx = max(0, current_det_pos - 10)
                        context_before = detected_text[start_idx:current_det_pos]
                        end_idx = min(len(detected_text), current_det_pos + 10)
                        context_after = detected_text[current_det_pos:end_idx]
                        
                        text_without_spaces = text.replace(' ', '')
                        
                        marker_position = None
                        # Traiter aussi les espaces manquants
                        if len(text_without_spaces) > 0 or text.strip() == '':
                            # Calculer la position du marqueur une seule fois pour le groupe
                            is_end_of_line = False
                            is_start_of_line = False
                            
                            if rect_idx > 0 and rect_idx < len(valid_rects_final):
                                rect_prev = valid_rects_final[rect_idx - 1]
                                rect_next = valid_rects_final[rect_idx]
                                if isinstance(rect_prev, RectangleWithLine) and isinstance(rect_next, RectangleWithLine):
                                    same_line = rect_prev.line_number == rect_next.line_number
                                else:
                                    same_line = _in_same_line(rect_prev, rect_next, avg_width)
                                is_end_of_line = not same_line and rect_idx > 0
                                is_start_of_line = not same_line and rect_idx < len(valid_rects_final)
                            elif rect_idx >= len(valid_rects_final):
                                is_end_of_line = True
                            elif rect_idx == 0:
                                is_start_of_line = True
                            
                            if rect_idx > 0 and rect_idx < len(valid_rects_final) and not is_end_of_line:
                                x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                                x2, y2, w2, h2 = valid_rects_final[rect_idx]
                                marker_x = (x1 + w1 + x2) // 2
                                marker_y = min(y1, y2) + max(h1, h2) // 2
                                marker_w = 20
                                marker_h = max(h1, h2)
                                marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                            elif is_end_of_line or (rect_idx > 0 and rect_idx >= len(valid_rects_final)):
                                if rect_idx > 0 and len(valid_rects_final) > 0:
                                    x, y, w, h = valid_rects_final[rect_idx - 1]
                                    spacing = max(20, int(avg_width * 0.5))
                                    marker_x = max(0, x - spacing)
                                    marker_position = (marker_x, y, 20, h)
                                elif len(valid_rects_final) > 0:
                                    x, y, w, h = valid_rects_final[-1]
                                    spacing = max(20, int(avg_width * 0.5))
                                    marker_x = max(0, x - spacing)
                                    marker_position = (marker_x, y, 20, h)
                                else:
                                    marker_position = (10, 10, 20, 30)
                            elif is_start_of_line or rect_idx == 0:
                                if rect_idx < len(valid_rects_final):
                                    x, y, w, h = valid_rects_final[rect_idx]
                                    spacing = max(20, int(avg_width * 0.5))
                                    marker_position = (x + w + spacing, y, 20, h)
                                elif len(valid_rects_final) > 0:
                                    x, y, w, h = valid_rects_final[0]
                                    spacing = max(20, int(avg_width * 0.5))
                                    marker_position = (x + w + spacing, y, 20, h)
                                else:
                                    marker_position = (10, 10, 20, 30)
                            
                            if marker_position and text.strip() != '':
                                mx, my, mw, mh = marker_position
                                cv2.line(result_image, (mx, my), (mx + mw, my + mh), (0, 0, 255), 3)
                                cv2.line(result_image, (mx + mw, my), (mx, my + mh), (0, 0, 255), 3)
                                cv2.rectangle(result_image, (mx - 5, my - 5), (mx + mw + 5, my + mh + 5), (0, 0, 255), 2)
                        
                        # Ajouter une seule erreur 'missing' pour tout le bloc
                        # Si c'est uniquement des espaces, créer quand même l'erreur
                        if text.strip() == '' and len(text) > 0:
                            # Uniquement des espaces manquants
                            if marker_position is None:
                                # Calculer une position par défaut
                                if rect_idx > 0 and len(valid_rects_final) > 0:
                                    x, y, w, h = valid_rects_final[rect_idx - 1]
                                    spacing = max(20, int(avg_width * 0.5))
                                    marker_x = max(0, x - spacing)
                                    marker_position = (marker_x, y, 20, h)
                                else:
                                    marker_position = (10, 10, 20, 30)
                            
                            differences_info.append({
                                'type': 'missing',
                                'text': ' ',  # Espace manquant
                                'position': rect_idx,
                                'context_before': context_before,
                                'context_after': context_after,
                                'marker_position': marker_position
                            })
                        else:
                            differences_info.append({
                                'type': 'missing',
                                'text': text,
                                'position': rect_idx,
                                'context_before': context_before,
                                'context_after': context_after,
                                'marker_position': marker_position
                            })
                        
                        i += 1
                
                elif op == 1:  # En trop
                    for char in text:
                        if char == ' ':
                            # Espace en trop dans le détecté
                            # Créer une erreur d'espace en trop
                            if rect_idx > 0 and rect_idx <= len(valid_rects_final):
                                # Positionner le marqueur entre les lettres
                                if rect_idx > 0:
                                    x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                                    if rect_idx < len(valid_rects_final):
                                        x2, y2, w2, h2 = valid_rects_final[rect_idx]
                                        marker_x = (x1 + w1 + x2) // 2
                                        marker_y = min(y1, y2) + max(h1, h2) // 2
                                        marker_w = 20
                                        marker_h = max(h1, h2)
                                        marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                                    else:
                                        spacing = max(20, int(avg_width * 0.5))
                                        marker_x = max(0, x1 - spacing)
                                        marker_position = (marker_x, y1, 20, h1)
                                else:
                                    marker_position = (10, 10, 20, 30)
                                
                                start_idx = max(0, current_det_pos - 10)
                                context_before = detected_text[start_idx:current_det_pos]
                                end_idx = min(len(detected_text), current_det_pos + 1 + 10)
                                context_after = detected_text[current_det_pos + 1:end_idx]
                                
                                differences_info.append({
                                    'type': 'extra',
                                    'text': ' ',  # Espace en trop
                                    'position': rect_idx,
                                    'context_before': context_before,
                                    'context_after': context_after,
                                    'marker_position': marker_position
                                })
                            current_det_pos += 1
                            continue
                        
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            color = (255, 0, 0)
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine) and valid_rects_final[rect_idx].color:
                                color = valid_rects_final[rect_idx].color
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                            
                            start_idx = max(0, current_det_pos - 10)
                            context_before = detected_text[start_idx:current_det_pos]
                            end_idx = min(len(detected_text), current_det_pos + 1 + 10)
                            context_after = detected_text[current_det_pos + 1:end_idx]
                            
                            differences_info.append({
                                'type': 'extra',
                                'text': char,
                                'position': rect_idx,
                                'rect': (x, y, w, h),
                                'context_before': context_before,
                                'context_after': context_after
                            })
                            rect_idx += 1
                        current_det_pos += 1
                    i += 1
    else:
        for rect in valid_rects_final:
            x, y, w, h = rect
            color = (0, 255, 0)
            if isinstance(rect, RectangleWithLine) and rect.color:
                color = rect.color
            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
    
    _, buffer = cv2.imencode('.jpg', result_image)
    image_base64 = base64.b64encode(buffer)
    
    missing_count = len([d for d in differences_info if d.get('type') == 'missing'])
    extra_count = len([d for d in differences_info if d.get('type') == 'extra'])
    wrong_count = len([d for d in differences_info if d.get('type') == 'wrong'])
    has_errors = (missing_count + extra_count + wrong_count) > 0
    
    paracha_status = "complete"
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        if reference_text:
            # Pour la couverture, on compare sans espaces pour éviter les biais
            detected_normalized = detected_text.replace(' ', '').replace('\n', '')
            reference_normalized = reference_text.replace(' ', '').replace('\n', '')
            
            len_detected = len(detected_normalized)
            len_reference = len(reference_normalized)
            
            if len_reference > 0:
                coverage_ratio = len_detected / len_reference if len_reference > 0 else 0
                last_chars_count = min(10, len_reference)
                last_chars_reference = reference_normalized[-last_chars_count:]
                
                if coverage_ratio < 0.90 or last_chars_reference not in detected_normalized:
                    paracha_status = "incomplete"
                    
                    # Si incomplète, retirer les erreurs 'missing' qui sont à la toute fin
                    # car elles sont dues à la coupure de l'image, pas à une erreur du sofer
                    removed_count = 0
                    while differences_info and differences_info[-1]['type'] == 'missing':
                        differences_info.pop()
                        removed_count += 1
                    
                    if removed_count > 0 and logger:
                        logger.info(f"Paracha incomplète : {removed_count} erreurs 'missing' finales retirées du rapport.")
    
    # Recalculer les comptes après filtrage éventuel
    missing_count = len([d for d in differences_info if d.get('type') == 'missing'])
    extra_count = len([d for d in differences_info if d.get('type') == 'extra'])
    wrong_count = len([d for d in differences_info if d.get('type') == 'wrong'])
    has_errors = (missing_count + extra_count + wrong_count) > 0
    
    return (
        image_base64,
        paracha_name,
        detected_text,
        differences_info,
        {
            "paracha_status": paracha_status,
            "has_errors": has_errors,
            "errors": {
                "missing": missing_count,
                "extra": extra_count,
                "wrong": wrong_count,
            },
        },
    )


def image_to_b64_string(image):
    _, buffer = cv2.imencode('.jpg', image)
    image_base64 = base64.b64encode(buffer)
    return image_base64.decode('utf-8')
