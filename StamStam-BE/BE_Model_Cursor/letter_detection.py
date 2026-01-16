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

from BE_Model_Cursor.utils.contour_detector import detect_and_order_contours
from BE_Model_Cursor.models.letter_predictor import predict_letters, letter_code_to_hebrew
from BE_Model_Cursor.comparison.paracha_matcher import detect_paracha


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
    
    # Détecter et ordonner les contours (sans prédiction des lettres)
    ordered_rects = detect_and_order_contours(image, min_contour_area=50)
    
    # Si aucun rectangle valide, retourner l'image originale
    if len(ordered_rects) == 0:
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer)
        return image_base64, "Aucune lettre détectée"
    
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

