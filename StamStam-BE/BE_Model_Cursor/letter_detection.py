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

from BE_Model_Cursor.utils.contour_detector import detect_and_order_contours, detect_contours, detect_contours
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.comparison.paracha_matcher import detect_paracha, load_paracha_texts
from BE_Model_Cursor.comparison.text_alignment import apply_segmentation_corrections
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
    # Calculer le chemin vers le backend
    backend_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Chemins par défaut
    if weight_file is None:
        weight_file = os.path.join(backend_dir_path, 'ocr', 'model', 'output', 'Nadam_beta_1_256_30.hdf5')
    
    if overflow_dir is None:
        overflow_dir = os.path.join(backend_dir_path, 'overflow')
    
    # Détecter et ordonner les contours (sans prédiction des lettres)
    ordered_rects = detect_and_order_contours(image, min_contour_area=50)
    
    # Si aucun rectangle valide, retourner l'image originale
    if len(ordered_rects) == 0:
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre détectée", ""
    
    # Identifier les lettres avec le modèle ML
    print(f"\n[detect_letters] Prédiction des lettres avec le modèle ML...")
    print(f"  Nombre de rectangles à prédire: {len(ordered_rects)}")
    letter_codes = predict_letters(image, ordered_rects, weight_file)
    print(f"  ✓ Prédiction terminée: {len(letter_codes)} codes obtenus")
    
    # Filtrer les codes invalides (27 = zevel/noise)
    valid_letter_data = [(rect, code) for rect, code in zip(ordered_rects, letter_codes) if code != 27]
    invalid_count = len(ordered_rects) - len(valid_letter_data)
    if invalid_count > 0:
        print(f"  ⚠ {invalid_count} rectangles filtrés (code 27 = zevel/noise)")
    
    if len(valid_letter_data) == 0:
        print(f"  ✗ ERREUR: Aucune lettre valide détectée après filtrage")
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre valide détectée", "", []
    
    # Extraire les rectangles et codes valides
    valid_rects_final, valid_codes = zip(*valid_letter_data)
    valid_rects_final = list(valid_rects_final)
    valid_codes = list(valid_codes)
    print(f"  ✓ {len(valid_rects_final)} lettres valides conservées")
    
    # Détecter la paracha et obtenir le texte
    print(f"\n[detect_letters] Détection de la paracha...")
    paracha_name, detected_text = detect_paracha(list(valid_codes), overflow_dir)
    
    # Appliquer les corrections de segmentation si une paracha a été détectée
    if paracha_name and paracha_name != "Non détectée" and paracha_name != "Aucune lettre détectée":
        # Charger le texte de référence de la paracha
        paracha_texts = load_paracha_texts(overflow_dir)
        reference_text = paracha_texts.get(paracha_name, '')
        
        if reference_text:
            print(f"\n[detect_letters] Application des corrections de segmentation pour {paracha_name}")
            print(f"Texte détecté (avant correction): {detected_text[:50]}...")
            print(f"Texte de référence: {reference_text[:50]}...")
            
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
            detected_text = ''.join([letter_code_to_hebrew(code) if code != 27 else '' 
                                    for code in valid_codes])
            
            if corrections:
                print(f"Corrections appliquées: {len(corrections)}")
                for corr in corrections:
                    print(f"  - {corr['type']} à la position {corr['position']}: {corr.get('text', '')}")
            
            print(f"Texte détecté (après correction): {detected_text[:50]}...")
            print(f"Nombre de rectangles après correction: {len(valid_rects_final)}")
            print(f"Nombre de codes après correction: {len(valid_codes)}")
    
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
            
            print(f"\n[detect_letters] Comparaison finale (marquage uniquement, pas de corrections):")
            print(f"  Texte de référence: {reference_text[:100]}...")
            print(f"  Texte détecté (après corrections de segmentation): {detected_text[:100]}...")
            print(f"  Nombre de rectangles: {len(valid_rects_final)}")
            print(f"  Nombre de caractères dans detected_text: {len(detected_text)}")
            
            # Mapper les différences aux rectangles
            # On parcourt le texte détecté caractère par caractère
            # IMPORTANT: On ne fait PLUS de corrections ici, seulement du marquage
            rect_idx = 0
            i = 0
            
            for i in range(len(diff)):
                op, text = diff[i]
                
                if op == 0:  # Égalité - texte correct (vert)
                    # Dessiner en vert pour chaque caractère correspondant
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Vert
                            rect_idx += 1
                    i += 1
                
                elif op == -1:  # Supprimé dans detected_text = lettre manquante dans le texte détecté
                    # Vérifier si c'est une substitution (suivi d'une addition)
                    if i + 1 < len(diff) and diff[i + 1][0] == 1:
                        # C'est une substitution : une lettre a été remplacée par une autre
                        added_text = diff[i + 1][1]
                        expected_text = text
                        
                        # Marquer comme "wrong" (lettre fausse)
                        for j in range(len(added_text)):
                            if rect_idx < len(valid_rects_final):
                                x, y, w, h = valid_rects_final[rect_idx]
                                cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 165, 255), 2)  # Orange
                                differences_info.append({
                                    'type': 'wrong',
                                    'text': added_text[j] if j < len(added_text) else '',
                                    'expected': expected_text[j] if j < len(expected_text) else expected_text,
                                    'position': rect_idx,
                                    'rect': (x, y, w, h)
                                })
                                rect_idx += 1
                        i += 1  # On passe l'opération -1, et +1 sera géré dans le prochain tour de boucle
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
                        # Si on a des rectangles avant et après, placer le marqueur entre eux
                        marker_position = None
                        if rect_idx > 0 and rect_idx < len(valid_rects_final):
                            # Position entre rect_idx-1 et rect_idx
                            x1, y1, w1, h1 = valid_rects_final[rect_idx - 1]
                            x2, y2, w2, h2 = valid_rects_final[rect_idx]
                            # Position au milieu entre les deux rectangles
                            marker_x = (x1 + w1 + x2) // 2
                            marker_y = min(y1, y2) + max(h1, h2) // 2
                            marker_w = 20
                            marker_h = max(h1, h2)
                            marker_position = (marker_x - marker_w // 2, marker_y, marker_w, marker_h)
                        elif rect_idx > 0:
                            # Position après le dernier rectangle
                            x, y, w, h = valid_rects_final[rect_idx - 1]
                            marker_position = (x - 30, y, 20, h)
                        elif rect_idx < len(valid_rects_final):
                            # Position avant le premier rectangle
                            x, y, w, h = valid_rects_final[rect_idx]
                            marker_position = (x + w + 10, y, 20, h)
                        
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
                
                elif op == 1:  # Ajouté dans detected_text = lettre en trop dans le texte détecté
                    # Dessiner en bleu pour chaque caractère en trop
                    for j in range(len(text)):
                        if rect_idx < len(valid_rects_final):
                            x, y, w, h = valid_rects_final[rect_idx]
                            cv2.rectangle(result_image, (x, y), (x + w, y + h), (255, 0, 0), 2)  # Bleu (BGR)
                            differences_info.append({
                                'type': 'extra',
                                'text': text[j] if j < len(text) else '',
                                'position': rect_idx,
                                'rect': (x, y, w, h)
                            })
                            rect_idx += 1
                    i += 1
    else:
        # Si pas de paracha détectée, dessiner tout en vert
        for x, y, w, h in valid_rects_final:
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Encoder l'image en base64
    _, buffer = cv2.imencode('.jpg', result_image)
    image_base64 = base64.b64encode(buffer)
    
    return image_base64, paracha_name, detected_text, differences_info

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

