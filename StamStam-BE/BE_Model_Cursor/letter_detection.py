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
from BE_Model_Cursor.utils.logger import get_logger
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
            
            # Recalculer le texte détecté en incluant la détection d'espaces
            detected_text = ''
            
            # Calculer la largeur moyenne
            if len(valid_rects_final) > 0:
                avg_width = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in valid_rects_final) / len(valid_rects_final)
            else:
                avg_width = 50
            
            # Seuil pour détecter un espace (45% de la largeur moyenne d'une lettre)
            space_threshold = avg_width * 0.45
            
            if debug:
                logger.debug(f"Détection espaces: Width moyenne={avg_width:.1f}, Seuil={space_threshold:.1f}")
            
            for i, rect in enumerate(valid_rects_final):
                # Ajouter la lettre
                letter = ''
                if isinstance(rect, RectangleWithLine) and rect.detected_letter:
                    letter = rect.detected_letter
                elif i < len(valid_codes):
                    letter = letter_code_to_hebrew(valid_codes[i]) if valid_codes[i] != 27 else ''
                
                detected_text += letter
                
                # Vérifier s'il faut ajouter un espace après cette lettre
                if i < len(valid_rects_final) - 1:
                    current_rect = valid_rects_final[i]
                    next_rect = valid_rects_final[i+1]
                    
                    same_line = False
                    if isinstance(current_rect, RectangleWithLine) and isinstance(next_rect, RectangleWithLine):
                        same_line = current_rect.line_number == next_rect.line_number
                    else:
                        same_line = _in_same_line(current_rect, next_rect, avg_width)
                    
                    if same_line:
                        # Calculer l'écart horizontal
                        # En hébreu (droite à gauche), current est à droite, next est à gauche
                        c_x = current_rect.x if isinstance(current_rect, RectangleWithLine) else current_rect[0]
                        n_x = next_rect.x if isinstance(next_rect, RectangleWithLine) else next_rect[0]
                        n_w = next_rect.w if isinstance(next_rect, RectangleWithLine) else next_rect[2]
                        
                        # L'espace est entre le début X de next+width et le début X de current
                        gap = c_x - (n_x + n_w)
                        
                        # CORRECTION LAMED : Si current_rect est un Lamed, sa "tête" peut réduire artificiellement le gap
                        # On vérifie si la lettre est un Lamed (code hébreu ou caractère)
                        is_lamed = False
                        if isinstance(current_rect, RectangleWithLine) and current_rect.detected_letter == 'ל':
                            is_lamed = True
                        elif i < len(valid_codes) and letter_code_to_hebrew(valid_codes[i]) == 'ל':
                            is_lamed = True
                            
                        gap_adjusted = gap
                        if is_lamed:
                            # On ajoute un bonus au gap car le Lamed a une tête qui dépasse à gauche
                            # On ajoute environ 30% de la largeur moyenne pour compenser
                            gap_adjusted += avg_width * 0.3
                        
                        if gap_adjusted > space_threshold:
                            detected_text += ' '
                            if debug:
                                logger.debug(f"  Espace détecté après {letter} (gap={gap:.1f}, adj={gap_adjusted:.1f} > {space_threshold:.1f})")
                        elif debug and gap_adjusted > space_threshold * 0.5:
                             logger.debug(f"  Pas d'espace après {letter} (gap={gap:.1f}, adj={gap_adjusted:.1f} <= {space_threshold:.1f})")
                    else:
                        # Changement de ligne : ajouter un espace
                        detected_text += ' '
            
            if debug:
                logger.debug(f"Texte détecté final: {detected_text}")
            
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
                        if len(text_without_spaces) > 0:
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
                            
                            if marker_position:
                                mx, my, mw, mh = marker_position
                                cv2.line(result_image, (mx, my), (mx + mw, my + mh), (0, 0, 255), 3)
                                cv2.line(result_image, (mx + mw, my), (mx, my + mh), (0, 0, 255), 3)
                                cv2.rectangle(result_image, (mx - 5, my - 5), (mx + mw + 5, my + mh + 5), (0, 0, 255), 2)
                        
                        # Ajouter une seule erreur 'missing' pour tout le bloc
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
