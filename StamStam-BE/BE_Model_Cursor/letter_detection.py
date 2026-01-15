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

from BE_Model_Cursor.utils.rectangle_sorter import sort_rectangles_by_lines
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.comparison.paracha_matcher import detect_paracha


def union_rect(a, b):
    """Combine deux rectangles en un rectangle englobant"""
    x = min(a[0], b[0])
    y = min(a[1], b[1])
    w = max(a[0] + a[2], b[0] + b[2]) - x
    h = max(a[1] + a[3], b[1] + b[3]) - y
    return (x, y, w, h)


def intersection_rect(a, b):
    """Calcule l'intersection de deux rectangles"""
    x = max(a[0], b[0])
    y = max(a[1], b[1])
    w = min(a[0] + a[2], b[0] + b[2]) - x
    h = min(a[1] + a[3], b[1] + b[3]) - y
    if w < 0 or h < 0:
        return None
    return (x, y, w, h)


def is_included(a, b):
    """Vérifie si le rectangle b est entièrement inclus dans le rectangle a"""
    return (a[0] <= b[0] and b[0] + b[2] <= a[0] + a[2] and
            a[1] <= b[1] and b[1] + b[3] <= a[1] + a[3])


def follow_rect(rect1, rect2, width_mean):
    """
    Vérifie si rect2 suit rect1 (même ligne mais peut-être pas de chevauchement vertical)
    Utilisé pour détecter des lettres comme ק qui ont des parties séparées
    """
    s = max(rect1[1], rect2[1])
    h = min(rect1[1] + rect1[3], rect2[1] + rect2[3]) - s
    # Si il y a un chevauchement vertical même minime et les rectangles sont proches horizontalement
    if h > 1 and (rect2[0] - (rect1[0] + rect1[2])) < width_mean * 8:
        return h
    return None


def combine_horizontal_overlaps(rects):
    """
    Combine les rectangles qui se chevauchent beaucoup horizontalement
    (similaire à is_horizontal_include de fix_issues_box)
    """
    if len(rects) < 2:
        return rects
    
    i = 0
    result = []
    
    while i < len(rects):
        current = rects[i]
        combined = False
        
        # Chercher un rectangle suivant qui se chevauche beaucoup
        for j in range(i + 1, len(rects)):
            other = rects[j]
            
            # Calculer le chevauchement horizontal
            x = max(current[0], other[0])
            w = min(current[0] + current[2], other[0] + other[2]) - x
            
            if w > 0:
                small_w = min(current[2], other[2])
                
                # Si le chevauchement est > 70% de la largeur du plus petit
                if w > 0.7 * small_w:
                    # Vérifier qu'ils sont sur la même ligne (chevauchement vertical)
                    s = max(current[1], other[1])
                    h_overlap = min(current[1] + current[3], other[1] + other[3]) - s
                    if h_overlap > 0:
                        # Combiner les rectangles
                        current = union_rect(current, other)
                        # Supprimer other de la liste
                        rects.pop(j)
                        combined = True
                        break
        
        result.append(current)
        i += 1
    
    return result


def group_letters_by_line(rects):
    """
    Groupe les rectangles en lignes et combine ceux qui font partie de la même lettre
    (similaire à sort_contour mais simplifié)
    """
    if not rects:
        return rects
    
    # Trier par position x décroissante
    width_mean = sum(r[2] for r in rects) / len(rects) if rects else 50
    rects = sorted(rects, key=lambda r: r[0] + r[2], reverse=True)
    
    lines = [rects[0:1]]  # Première ligne avec le premier rectangle
    
    for i in range(1, len(rects)):
        current_rect = rects[i]
        added = False
        
        # Chercher dans les lignes existantes (derniers rectangles de chaque ligne)
        for line_idx, line in enumerate(lines):
            # Vérifier avec les derniers rectangles de la ligne
            for j in range(max(0, len(line) - 3), len(line)):
                last_rect = line[j]
                h = follow_rect(current_rect, last_rect, width_mean)
                
                if h:
                    # Vérifier que current n'est pas inclus dans un rectangle existant
                    is_included_in_line = False
                    for existing_rect in line:
                        if is_included(existing_rect, current_rect):
                            is_included_in_line = True
                            break
                    
                    if not is_included_in_line:
                        lines[line_idx].append(current_rect)
                        added = True
                        break
            
            if added:
                break
        
        if not added:
            # Nouvelle ligne
            lines.append([current_rect])
    
    # Retourner la liste aplatie
    return [rect for line in lines for rect in line]


def remove_small_included_rects(rects):
    """Supprime les rectangles qui sont entièrement inclus dans d'autres"""
    if len(rects) < 2:
        return rects
    
    result = []
    for i, rect_a in enumerate(rects):
        is_included_flag = False
        for j, rect_b in enumerate(rects):
            if i != j and is_included(rect_b, rect_a):
                is_included_flag = True
                break
        if not is_included_flag:
            result.append(rect_a)
    
    return result


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


def detect_letters(image, weight_file=None, overflow_dir=None):
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
        tuple: (image_base64, paracha_name) où image_base64 est l'image encodée en base64
               avec les rectangles verts autour des lettres, et paracha_name est le nom
               de la paracha détectée
    """
    # Calculer le chemin vers le backend
    backend_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Chemins par défaut
    if weight_file is None:
        weight_file = os.path.join(backend_dir_path, 'ocr', 'model', 'output', 'Nadam_beta_1_256_30.hdf5')
    
    if overflow_dir is None:
        overflow_dir = os.path.join(backend_dir_path, 'overflow')
    
    # Convertir en niveaux de gris
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Appliquer un flou gaussien pour réduire le bruit
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Seuillage adaptatif pour binariser l'image
    # On inverse pour avoir les lettres en blanc sur fond noir
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
    
    # Filtrer les contours par taille (similaire à get_contour)
    MIN_CONTOUR_AREA = 50
    valid_rects = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_CONTOUR_AREA:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filtres similaires à get_contour: w > 5, h > 8, w < 1000
        if w > 5 and h > 8 and w < 1000:
            # Filtrer par ratio raisonnable
            aspect_ratio = w / h if h > 0 else 0
            if 0.1 < aspect_ratio < 5.0:
                valid_rects.append((x, y, w, h))
    
    # Supprimer les rectangles inclus dans d'autres
    valid_rects = remove_small_included_rects(valid_rects)
    
    # Grouper les rectangles par ligne (pour combiner les parties de ק, ה, etc.)
    valid_rects = group_letters_by_line(valid_rects)
    
    # Combiner les rectangles qui se chevauchent horizontalement
    valid_rects = combine_horizontal_overlaps(valid_rects)
    
    # Si aucun rectangle valide, retourner l'image originale
    if len(valid_rects) == 0:
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre détectée"
    
    # Ordonner les rectangles de droite à gauche et de haut en bas (ordre hébreu)
    ordered_rects = sort_rectangles_by_lines(valid_rects)
    
    # Identifier les lettres avec le modèle ML
    letter_codes = predict_letters(image, ordered_rects, weight_file)
    
    # Filtrer les codes invalides (27 = zevel/noise)
    valid_letter_data = [(rect, code) for rect, code in zip(ordered_rects, letter_codes) if code != 27]
    
    if len(valid_letter_data) == 0:
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre valide détectée"
    
    # Extraire les rectangles et codes valides
    valid_rects_final, valid_codes = zip(*valid_letter_data)
    
    # Détecter la paracha
    paracha_name = detect_paracha(list(valid_codes), overflow_dir)
    
    # Créer une copie de l'image originale pour dessiner les rectangles
    result_image = image.copy()
    
    # Dessiner les rectangles verts autour des lettres détectées
    for x, y, w, h in valid_rects_final:
        cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Encoder l'image en base64
    _, buffer = cv2.imencode('.jpg', result_image)
    image_base64 = base64.b64encode(buffer)
    
    return image_base64, paracha_name

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

