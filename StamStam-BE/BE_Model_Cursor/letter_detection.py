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
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        
    Returns:
        numpy array: Image recadrée du parchemin
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
    
    Args:
        image: Image OpenCV complète (numpy array) en couleur BGR
        rect: Tuple (x, y, w, h) représentant le rectangle à analyser
        min_contour_area: Surface minimale d'un contour pour être considéré (défaut: 30, plus petit que la détection normale)
        
    Returns:
        list: Liste de tuples (x, y, w, h) représentant les rectangles détectés dans la région
              Les coordonnées sont relatives à l'image complète (pas à la région extraite)
    """
    x, y, w, h = rect
    
    # Extraire la région de l'image
    # S'assurer que les coordonnées sont dans les limites de l'image
    x = max(0, int(x))
    y = max(0, int(y))
    w = min(image.shape[1] - x, int(w))
    h = min(image.shape[0] - y, int(h))
    
    if w <= 0 or h <= 0:
        return []
    
    region = image[y:y+h, x:x+w]
    
    if region.size == 0:
        return []
    
    # Détecter les contours dans cette région (sans combinaison des chevauchements)
    # On utilise directement detect_contours qui ne fait pas la combinaison
    # mais on doit éviter d'appeler combine_horizontal_overlaps
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
    
    # Filtrage des contours par taille (sans combinaison)
    valid_rects = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_contour_area:
            continue
        
        rx, ry, rw, rh = cv2.boundingRect(contour)
        
        # Filtres: w > 5, h > 8, w < 1000, ratio raisonnable
        if rw > 5 and rh > 8 and rw < 1000:
            aspect_ratio = rw / rh if rh > 0 else 0
            if 0.1 < aspect_ratio < 5.0:
                valid_rects.append((rx, ry, rw, rh))
    
    # Trier les rectangles de droite à gauche (ordre hébreu)
    # Les rectangles avec x + w plus grand sont à droite (début du texte hébreu)
    valid_rects.sort(key=lambda r: r[0] + r[2], reverse=True)
    
    # Convertir les coordonnées relatives à la région en coordonnées absolues dans l'image
    absolute_rects = []
    for rx, ry, rw, rh in valid_rects:
        # Coordonnées absolues dans l'image complète
        abs_x = x + rx
        abs_y = y + ry
        absolute_rects.append((abs_x, abs_y, rw, rh))
    
    return absolute_rects


def detect_letters(image, weight_file=None, overflow_dir=None, debug=False):
    """
    Détecte les lettres hébraïques dans une image, les ordonne, les identifie avec le modèle ML,
    compare avec les parachot et retourne l'image avec les rectangles ET le nom de la paracha.
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        weight_file: Chemin vers le fichier de poids du modèle (.hdf5). 
                     Si None, utilise le chemin par défaut.
        overflow_dir: Chemin vers le dossier overflow/ contenant les fichiers texte des parachot.
                      Si None, utilise le chemin relatif depuis le backend.
        
    Returns:
        tuple: (image_base64, paracha_name, detected_text) où image_base64 est l'image encodée en base64
               avec les rectangles verts autour des lettres, paracha_name est le nom
               de la paracha détectée, et detected_text est le texte hébreu détecté
    """
    # Chemins par défaut depuis config si disponible, sinon calcul relatif
    # Calculer backend_dir_path une seule fois au début
    backend_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if weight_file is None:
        try:
            # Essayer d'utiliser config.py (disponible depuis app.py)
            from config import config as app_config
            weight_file = app_config.MODEL_PATH
        except ImportError:
            # Si config.py n'est pas disponible (tests, etc.), utiliser chemin relatif
            weight_file = os.path.join(backend_dir_path, 'ocr', 'model', 'output', 'Nadam_beta_1_256_30.hdf5')
    
    if overflow_dir is None:
        try:
            from config import config as app_config
            overflow_dir = app_config.OVERFLOW_DIR
        except ImportError:
            # Si config.py n'est pas disponible (tests, etc.), utiliser chemin relatif
            overflow_dir = os.path.join(backend_dir_path, 'overflow')
    
    # Initialiser le logger
    logger = get_logger(__name__, debug=debug)
    
    # Détecter et ordonner les contours (sans prédiction des lettres)
    ordered_rects = detect_and_order_contours(image, min_contour_area=50)
    
    # Si aucun rectangle valide, retourner l'image originale
    if len(ordered_rects) == 0:
        logger.warning("Aucune lettre détectée dans l'image")
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre détectée", "", []
    
    # Identifier les lettres avec le modèle ML
    if debug:
        logger.debug(f"Prédiction des lettres avec le modèle ML...")
        logger.debug(f"Nombre de rectangles à prédire: {len(ordered_rects)}")
    letter_codes = predict_letters(image, ordered_rects, weight_file)
    if debug:
        logger.debug(f"Prédiction terminée: {len(letter_codes)} codes obtenus")
        
        # Afficher les lettres détectées interactivement
        predicted_labels = []
        for code in letter_codes:
            if code == 27:
                predicted_labels.append("?")
            else:
                # Utiliser le nom de la lettre ou le code si l'affichage hébreu pose problème
                # On essaie d'afficher la lettre hébraïque
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
    
    # Initialiser detected_letter pour chaque RectangleWithLine
    for rect, code in zip(ordered_rects, letter_codes):
        if isinstance(rect, RectangleWithLine):
            rect.detected_letter = letter_code_to_hebrew(code) if code != 27 else None
    
    # Filtrer les codes invalides (27 = zevel/noise)
    valid_letter_data = [(rect, code) for rect, code in zip(ordered_rects, letter_codes) if code != 27]
    invalid_count = len(ordered_rects) - len(valid_letter_data)
    if invalid_count > 0:
        logger.debug(f"{invalid_count} rectangles filtrés (code 27 = zevel/noise)")
    
    if len(valid_letter_data) == 0:
        logger.error("Aucune lettre valide détectée après filtrage")
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre valide détectée", "", []
    
    # Extraire les rectangles et codes valides
    valid_rects_final, valid_codes = zip(*valid_letter_data)
    valid_rects_final = list(valid_rects_final)
    valid_codes = list(valid_codes)
    
    # Initialiser text_position pour chaque RectangleWithLine
    for i, rect in enumerate(valid_rects_final):
        if isinstance(rect, RectangleWithLine):
            rect.text_position = i
    
    if debug:
        logger.debug(f"{len(valid_rects_final)} lettres valides conservées")
    
    # Détecter la paracha et obtenir le texte
    if debug:
        logger.debug(f"Détection de la paracha...")
    paracha_name, detected_text = detect_paracha(list(valid_codes), overflow_dir)
    
    # Initialiser reference_text pour éviter les erreurs
    reference_text = ''
    
    # Appliquer les corrections de segmentation si une paracha a été détectée
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        # Charger le texte de référence de la paracha
        paracha_texts = load_paracha_texts(overflow_dir)
        reference_text = paracha_texts.get(paracha_name, '')
        
        if reference_text:
            if debug:
                logger.debug(f"Application des corrections de segmentation pour {paracha_name}")
                logger.debug(f"Texte détecté (avant correction): {detected_text[:50]}...")
                logger.debug(f"Texte de référence: {reference_text[:50]}...")
            
            # Appliquer les corrections
            corrected_rects, corrected_codes, corrections = apply_segmentation_corrections(
                valid_rects_final,
                valid_codes,
                reference_text,
                image,
                weight_file,
                debug=debug
            )
            
            # TOUJOURS utiliser les rectangles et codes corrigés (même si aucune correction n'a été appliquée)
            # car apply_segmentation_corrections peut avoir fait des ajustements
            valid_rects_final = corrected_rects
            valid_codes = corrected_codes
            
            # Recalculer le texte détecté avec les corrections
            # C'est ce texte corrigé qui sera comparé avec le texte de référence
            # Utiliser detected_letter depuis RectangleWithLine si disponible
            detected_text = ''
            for i, rect in enumerate(valid_rects_final):
                if isinstance(rect, RectangleWithLine) and rect.detected_letter:
                    detected_text += rect.detected_letter
                elif i < len(valid_codes):
                    # Fallback : utiliser le code si detected_letter n'est pas disponible
                    detected_text += letter_code_to_hebrew(valid_codes[i]) if valid_codes[i] != 27 else ''
            
            # Mettre à jour les couleurs des rectangles en fonction des différences
            # On calcule d'abord le diff pour déterminer les couleurs
            dmp = dmp_module.diff_match_patch()
            diff = dmp.diff_main(reference_text, detected_text)
            dmp.diff_cleanupSemantic(diff)
            
            # Parcourir le diff et mettre à jour les couleurs des rectangles
            # Utiliser une boucle while pour gérer les sauts d'index (substitutions)
            rect_idx = 0
            i = 0
            while i < len(diff):
                op, text = diff[i]
                
                if op == 0:  # Égalité - texte correct (vert)
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                valid_rects_final[rect_idx].color = (0, 255, 0)  # Vert
                            rect_idx += 1
                    i += 1
                
                elif op == -1:  # Supprimé dans detected_text = lettre manquante ou substitution
                    # Vérifier si c'est une substitution (suivi d'une addition)
                    if i + 1 < len(diff) and diff[i + 1][0] == 1:
                        # C'est une substitution : marquer en orange
                        added_text = diff[i + 1][1]
                        for j in range(len(added_text)):
                            if rect_idx < len(valid_rects_final):
                                if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                    valid_rects_final[rect_idx].color = (0, 165, 255)  # Orange
                                rect_idx += 1
                        i += 2  # On passe l'opération -1 ET +1
                    else:
                        # Pour les vraies lettres manquantes, pas de rectangle à colorer (on dessine un X)
                        i += 1
                
                elif op == 1:  # Ajouté dans detected_text = lettre en trop (bleu)
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                valid_rects_final[rect_idx].color = (255, 0, 0)  # Bleu
                            rect_idx += 1
                    i += 1
            
            if corrections:
                if debug:
                    logger.debug(f"Corrections appliquées: {len(corrections)}")
                    for corr in corrections:
                        logger.debug(f"  - {corr['type']} à la position {corr['position']}: {corr.get('text', '')}")
            
            if debug:
                logger.debug(f"Texte détecté (après correction): {detected_text[:50]}...")
                logger.debug(f"Nombre de rectangles après correction: {len(valid_rects_final)}")
                logger.debug(f"Nombre de codes après correction: {len(valid_codes)}")
    
    # Créer une copie de l'image originale pour dessiner les rectangles
    result_image = image.copy()
    
    # Calculer les différences et dessiner avec des couleurs différentes
    # IMPORTANT: On utilise detected_text qui a été recalculé APRÈS les corrections de segmentation
    # Donc si une fusion a réussi, le rectangle fusionné correspondra au texte de référence
    # et sera marqué en vert (correct) et non en bleu (en trop)
    differences_info = []
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        paracha_texts = load_paracha_texts(overflow_dir)
        reference_text = paracha_texts.get(paracha_name, '')
        
        if reference_text:
            # Calculer les différences
            # On compare detected_text (APRÈS corrections) avec reference_text pour trouver :
            # - Lettres en plus dans detected_text (par rapport à reference) = extra
            # - Lettres en moins dans detected_text (par rapport à reference) = missing
            # Si une fusion a réussi, detected_text contient déjà la lettre fusionnée
            # et elle sera marquée comme correcte (vert) si elle correspond au texte de référence
            dmp = dmp_module.diff_match_patch()
            diff = dmp.diff_main(reference_text, detected_text)
            dmp.diff_cleanupSemantic(diff)
            
            if debug:
                logger.debug(f"Comparaison finale (marquage uniquement, pas de corrections):")
                logger.debug(f"  Texte de référence: {reference_text[:100]}...")
                logger.debug(f"  Texte détecté (après corrections de segmentation): {detected_text[:100]}...")
                logger.debug(f"  Nombre de rectangles: {len(valid_rects_final)}")
                logger.debug(f"  Nombre de caractères dans detected_text: {len(detected_text)}")
            
            # Mapper les différences aux rectangles et dessiner
            # On parcourt le texte détecté caractère par caractère
            # IMPORTANT: On ne fait PLUS de corrections ici, seulement du marquage
            # Les couleurs ont déjà été mises à jour dans les rectangles précédemment
            rect_idx = 0
            i = 0
            current_det_pos = 0  # Position actuelle dans detected_text
            
            while i < len(diff):
                op, text = diff[i]
                
                if op == 0:  # Égalité - texte correct (vert)
                    # Dessiner en utilisant la couleur du rectangle
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            # Utiliser la couleur du rectangle si disponible, sinon vert par défaut
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                color = valid_rects_final[rect_idx].color
                            else:
                                color = (0, 255, 0)  # Vert par défaut
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                            rect_idx += 1
                    
                    current_det_pos += len(text)
                    i += 1
                
                elif op == -1:  # Supprimé dans detected_text = lettre manquante dans le texte détecté (MISSING)
                    # Vérifier si c'est une substitution (suivi d'une addition)
                    if i + 1 < len(diff) and diff[i + 1][0] == 1:
                        # C'est une substitution : une lettre a été remplacée par une autre
                        added_text = diff[i + 1][1]
                        expected_text = text
                        
                        # Calculer le contexte (autour de added_text dans detected_text)
                        context_before = ""
                        context_after = ""
                        
                        start_idx = max(0, current_det_pos - 10)
                        context_before = detected_text[start_idx:current_det_pos]
                        
                        end_idx = min(len(detected_text), current_det_pos + len(added_text) + 10)
                        context_after = detected_text[current_det_pos + len(added_text):end_idx]
                        
                        # Marquer comme "wrong" (lettre fausse)
                        for j in range(len(added_text)):
                            if rect_idx < len(valid_rects_final):
                                x, y, w, h = valid_rects_final[rect_idx]
                                # Utiliser la couleur du rectangle si disponible, sinon orange par défaut
                                if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                    color = valid_rects_final[rect_idx].color
                                else:
                                    color = (0, 165, 255)  # Orange par défaut
                                cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                                differences_info.append({
                                    'type': 'wrong',
                                    'text': added_text[j] if j < len(added_text) else '',
                                    'expected': expected_text[j] if j < len(expected_text) else expected_text,
                                    'position': rect_idx,
                                    'rect': (x, y, w, h),
                                    'context_before': context_before,
                                    'context_after': context_after
                                })
                                rect_idx += 1
                        
                        current_det_pos += len(added_text)
                        i += 2  # On passe l'opération -1 ET +1
                    else:
                        # Vraie lettre manquante (pas de rectangle correspondant)
                        expected_char = text[0] if text else ''  # La lettre attendue
                        
                        # Calculer le contexte (mots avant et après)
                        context_before = ''
                        context_after = ''
                        
                        # Position dans le texte de référence
                        ref_pos = sum(len(diff[j][1]) for j in range(i) if diff[j][0] == 0 or diff[j][0] == -1)
                        
                        # Prendre quelques caractères avant et après dans le texte de référence
                        context_size = 10  # Nombre de caractères de contexte
                        start_pos = max(0, ref_pos - context_size)
                        end_pos = min(len(reference_text), ref_pos + len(text) + context_size)
                        
                        context_before = reference_text[start_pos:ref_pos]
                        context_after = reference_text[ref_pos + len(text):end_pos]
                        
                        # Calculer la position approximative dans l'image
                        # IMPORTANT: valid_rects_final est ordonné de droite à gauche (ordre hébreu)
                        # Donc valid_rects_final[0] est le plus à droite (début du texte)
                        # et valid_rects_final[-1] est le plus à gauche (fin du texte)
                        marker_position = None
                        
                        # Calculer la largeur moyenne une fois au début (utilisée pour plusieurs choses)
                        if len(valid_rects_final) > 0:
                            avg_width = sum(r[2] if not isinstance(r, RectangleWithLine) else r.w for r in valid_rects_final) / len(valid_rects_final)
                        else:
                            avg_width = 50
                        
                        # Vérifier si on est à la fin d'une ligne
                        is_end_of_line = False
                        # Vérifier si on est au début d'une ligne (mais pas au début absolu)
                        is_start_of_line = False
                        
                        if rect_idx > 0 and rect_idx < len(valid_rects_final):
                            # Vérifier si rect_idx-1 et rect_idx sont sur la même ligne
                            rect_prev = valid_rects_final[rect_idx - 1]
                            rect_next = valid_rects_final[rect_idx]
                            
                            # Utiliser line_number si disponible, sinon _in_same_line pour compatibilité
                            if isinstance(rect_prev, RectangleWithLine) and isinstance(rect_next, RectangleWithLine):
                                same_line = rect_prev.line_number == rect_next.line_number
                            else:
                                # Compatibilité avec les tuples (avg_width déjà calculé plus haut)
                                same_line = _in_same_line(rect_prev, rect_next, avg_width)
                            
                            # Si les rectangles ne sont PAS sur la même ligne :
                            # - rect_idx-1 est à la fin d'une ligne
                            # - rect_idx est au début d'une nouvelle ligne
                            is_end_of_line = not same_line and rect_idx > 0  # Fin de ligne si rect_idx-1 existe
                            is_start_of_line = not same_line and rect_idx < len(valid_rects_final)  # Début de ligne si rect_idx existe
                        elif rect_idx >= len(valid_rects_final):
                            # Si on a traité tous les rectangles, on est forcément à la fin
                            is_end_of_line = True
                        elif rect_idx == 0:
                            # Si rect_idx == 0, on est au début absolu
                            is_start_of_line = True
                        
                        if rect_idx > 0 and rect_idx < len(valid_rects_final) and not is_end_of_line:
                            # Cas 1: Lettre manquante entre deux rectangles détectés (même ligne)
                            # Position entre rect_idx-1 et rect_idx
                            x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                            x2, y2, w2, h2 = valid_rects_final[rect_idx]
                            # Position au milieu entre les deux rectangles
                            # En hébreu: rect_idx-1 est à droite, rect_idx est à gauche
                            # La lettre manquante est entre les deux
                            marker_x = (x1 + w1 + x2) // 2
                            marker_y = min(y1, y2) + max(h1, h2) // 2
                            marker_w = 20
                            marker_h = max(h1, h2)
                            marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                        elif is_end_of_line or (rect_idx > 0 and rect_idx >= len(valid_rects_final)):
                            # Cas 2: Lettre manquante à la fin de la ligne
                            # Soit rect_idx-1 et rect_idx ne sont pas sur la même ligne,
                            # soit on a traité tous les rectangles
                            # Utiliser le dernier rectangle traité (rect_idx - 1) qui est sur la même ligne
                            if rect_idx > 0 and len(valid_rects_final) > 0:
                                # Le dernier rectangle traité est celui qui précède la lettre manquante
                                x, y, w, h = valid_rects_final[rect_idx - 1]
                                # Calculer un espacement basé sur la largeur moyenne
                                spacing = max(20, int(avg_width * 0.5))  # Au moins 20px ou 50% de la largeur moyenne
                                # En hébreu (droite à gauche), la fin est à gauche
                                # Placer le marqueur à gauche du dernier rectangle traité
                                marker_x = max(0, x - spacing)  # S'assurer qu'on ne sort pas de l'image
                                marker_position = (marker_x, y, 20, h)
                            elif len(valid_rects_final) > 0:
                                # Fallback : utiliser le dernier rectangle de toute l'image
                                x, y, w, h = valid_rects_final[-1]
                                spacing = max(20, int(avg_width * 0.5))
                                marker_x = max(0, x - spacing)
                                marker_position = (marker_x, y, 20, h)
                            else:
                                # Pas de rectangles du tout - position par défaut
                                marker_position = (10, 10, 20, 30)
                        elif rect_idx > 0 and rect_idx < len(valid_rects_final):
                            # Cas intermédiaire (ne devrait pas arriver avec la logique ci-dessus, mais sécurité)
                            # Si is_end_of_line est False mais qu'on arrive ici, traiter comme Cas 1
                            x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                            x2, y2, w2, h2 = valid_rects_final[rect_idx]
                            marker_x = (x1 + w1 + x2) // 2
                            marker_y = min(y1, y2) + max(h1, h2) // 2
                            marker_w = 20
                            marker_h = max(h1, h2)
                            marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                        elif is_start_of_line or rect_idx == 0:
                            # Cas 3: Lettre manquante au début d'une ligne
                            # Le début du texte est à droite (ordre hébreu), donc à droite du premier rectangle de la ligne
                            if rect_idx < len(valid_rects_final):
                                # Utiliser le rectangle suivant (rect_idx) qui est le premier de la nouvelle ligne
                                x, y, w, h = valid_rects_final[rect_idx]
                                # Calculer un espacement basé sur la largeur moyenne
                                spacing = max(20, int(avg_width * 0.5))
                                # Placer à droite du rectangle (début de ligne en hébreu = à droite)
                                marker_position = (x + w + spacing, y, 20, h)
                            elif len(valid_rects_final) > 0:
                                # Fallback : utiliser le premier rectangle (le plus à droite)
                                x, y, w, h = valid_rects_final[0]
                                spacing = max(20, int(avg_width * 0.5))
                                marker_position = (x + w + spacing, y, 20, h)
                            else:
                                # Pas de rectangles du tout - position par défaut
                                marker_position = (10, 10, 20, 30)
                        
                        # Dessiner un marqueur visuel pour la lettre manquante
                        if marker_position:
                            mx, my, mw, mh = marker_position
                            # Dessiner un X rouge pour indiquer la lettre manquante
                            cv2.line(result_image, (mx, my), (mx + mw, my + mh), (0, 0, 255), 3)  # Rouge
                            cv2.line(result_image, (mx + mw, my), (mx, my + mh), (0, 0, 255), 3)  # Rouge
                            # Dessiner aussi un rectangle pointillé autour
                            cv2.rectangle(result_image, (mx - 5, my - 5), (mx + mw + 5, my + mh + 5), (0, 0, 255), 2)
                        
                        differences_info.append({
                            'type': 'missing',
                            'text': text,
                            'position': rect_idx,
                            'context_before': context_before,
                            'context_after': context_after,
                            'marker_position': marker_position
                        })
                        
                        # Ne pas avancer rect_idx car il n'y a pas de rectangle dans detected_text
                        i += 1
                
                elif op == 1:  # Ajouté dans detected_text = lettre en trop dans le texte détecté (EXTRA)
                    # Dessiner en utilisant la couleur du rectangle
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            # Utiliser la couleur du rectangle si disponible, sinon bleu par défaut
                            if isinstance(valid_rects_final[rect_idx], RectangleWithLine):
                                color = valid_rects_final[rect_idx].color
                            else:
                                color = (255, 0, 0)  # Bleu par défaut
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                            
                            # Calculer le contexte pour extra (DANS DETECTED)
                            context_before = ""
                            context_after = ""
                            
                            start_idx = max(0, current_det_pos - 10)
                            context_before = detected_text[start_idx:current_det_pos]
                            
                            end_idx = min(len(detected_text), current_det_pos + len(text) + 10)
                            context_after = detected_text[current_det_pos + len(text):end_idx]
                            
                            differences_info.append({
                                'type': 'extra',
                                'text': text[j] if j < len(text) else '',
                                'position': rect_idx,
                                'rect': (x, y, w, h),
                                'context_before': context_before,
                                'context_after': context_after
                            })
                            rect_idx += 1
                    
                    current_det_pos += len(text)
                    i += 1
    else:
        # Si pas de paracha détectée, dessiner tout en vert (ou utiliser la couleur du rectangle)
        for rect in valid_rects_final:
            if isinstance(rect, RectangleWithLine):
                x, y, w, h = rect
                color = rect.color
            else:
                x, y, w, h = rect
                color = (0, 255, 0)  # Vert par défaut
            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
    
    # Encoder l'image en base64
    _, buffer = cv2.imencode('.jpg', result_image)
    image_base64 = base64.b64encode(buffer)
    
    # Calcul du statut et des erreurs pour le front
    missing_count = len([d for d in differences_info if d.get('type') == 'missing'])
    extra_count = len([d for d in differences_info if d.get('type') == 'extra'])
    wrong_count = len([d for d in differences_info if d.get('type') == 'wrong'])
    has_errors = (missing_count + extra_count + wrong_count) > 0
    
    # Déterminer si la paracha est complète ou incomplète
    # Une paracha est "חלקית" (incomplète) seulement si le texte détecté ne va pas jusqu'au bout
    # de la paracha de référence, indépendamment des erreurs (missing, extra, wrong)
    paracha_status = "complete"  # Par défaut, on considère que c'est complet
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        if reference_text:
            # Normaliser les textes (enlever les espaces) pour comparer
            detected_normalized = detected_text.replace(' ', '').replace('\n', '').replace('\r', '')
            reference_normalized = reference_text.replace(' ', '').replace('\n', '').replace('\r', '')
            
            # Si le texte détecté est significativement plus court (plus de 10% plus court)
            # OU si les dernières lettres de la référence ne sont pas présentes dans le texte détecté
            len_detected = len(detected_normalized)
            len_reference = len(reference_normalized)
            
            if len_reference > 0:
                # Vérifier si le texte détecté couvre au moins 90% de la référence
                coverage_ratio = len_detected / len_reference if len_reference > 0 else 0
                
                # Vérifier si les dernières lettres de la référence sont présentes
                # Prendre les 10 dernières lettres de la référence (ou moins si la référence est courte)
                last_chars_count = min(10, len_reference)
                last_chars_reference = reference_normalized[-last_chars_count:]
                
                # Si le texte détecté ne contient pas les dernières lettres de la référence
                # OU si la couverture est inférieure à 90%, alors c'est incomplet
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
    """
    Convertit une image OpenCV en string base64.
    
    Args:
        image: Image OpenCV (numpy array)
        
    Returns:
        str: String base64 de l'image
    """
    _, buffer = cv2.imencode('.jpg', image)
    image_base64 = base64.b64encode(buffer)
    return image_base64.decode('utf-8')
