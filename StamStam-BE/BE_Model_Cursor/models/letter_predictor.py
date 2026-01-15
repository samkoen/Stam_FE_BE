"""
Module pour identifier les lettres hébraïques à partir de rectangles d'image
en utilisant le modèle ML (LeNet)
"""
import cv2
import numpy as np
import os
import sys

# Ajouter le chemin vers ocr/model pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from ocr.model import image_to_np2
from ocr.model.lenet import LeNet
from keras import optimizers

# Cache global pour le modèle (évite de le recharger à chaque requête)
_model_cache = {}


def extract_letter_images(image, rects):
    """
    Extrait les régions d'image correspondant à chaque rectangle et les prépare pour le modèle.
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        
    Returns:
        numpy array: Array d'images préparées (28x28 en niveaux de gris)
    """
    letter_images = []
    
    for x, y, w, h in rects:
        # Extraire la région du rectangle
        img_rect = image[y:y+h, x:x+w]
        
        # Convertir en niveaux de gris
        img_gray = cv2.cvtColor(img_rect, cv2.COLOR_BGR2GRAY)
        
        # Redimensionner à 28x28 (taille attendue par le modèle)
        img_2828 = cv2.resize(img_gray, (28, 28))
        
        letter_images.append(img_2828)
    
    # Convertir en numpy array
    return np.array(letter_images)


def _load_model(weight_file):
    """
    Charge le modèle LeNet et le met en cache pour éviter de le recharger à chaque requête.
    
    Args:
        weight_file: Chemin vers le fichier de poids du modèle (.hdf5)
        
    Returns:
        Le modèle Keras compilé
    """
    global _model_cache
    
    # Vérifier si le modèle est déjà en cache
    cache_key = weight_file
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    # Charger le modèle une seule fois
    print(f"[letter_predictor] Chargement du modèle depuis {weight_file}...")
    model = LeNet.build(
        numChannels=1,
        imgRows=image_to_np2.WIDTH,
        imgCols=image_to_np2.HEIGHT,
        numClasses=30,
        weightsPath=weight_file
    )
    
    # Compiler le modèle
    model.compile(
        loss="categorical_crossentropy",
        optimizer=optimizers.Adagrad(),
        metrics=["accuracy"]
    )
    
    # Mettre en cache
    _model_cache[cache_key] = model
    print(f"[letter_predictor] Modèle chargé et mis en cache")
    
    return model


def predict_letters(image, rects, weight_file):
    """
    Identifie les lettres hébraïques dans les rectangles donnés en utilisant le modèle ML.
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        weight_file: Chemin vers le fichier de poids du modèle (.hdf5)
        
    Returns:
        list: Liste des codes de lettres prédits (0-29, où 27 = zevel/noise)
    """
    if len(rects) == 0:
        return []
    
    # Extraire les images des lettres
    letter_images = extract_letter_images(image, rects)
    
    # Préparer les données (même format que lenet_stam_predict)
    test_data = letter_images.reshape((letter_images.shape[0], image_to_np2.WIDTH, image_to_np2.HEIGHT, 1))
    test_data = test_data.astype("float32") / 255.0
    
    # Charger le modèle (mise en cache automatique)
    model = _load_model(weight_file)
    
    # Faire les prédictions
    predictions = []
    for i in range(len(test_data)):
        probs = model.predict(test_data[np.newaxis, i], batch_size=128, verbose=0)
        prediction = probs.argmax(axis=1)
        predictions.append(prediction[0])
    
    return predictions


def letter_code_to_hebrew(letter_code):
    """
    Convertit un code de lettre (0-29) en caractère hébreu.
    
    Args:
        letter_code: Code de la lettre (0-29, où 27 = zevel/noise)
        
    Returns:
        str: Caractère hébreu correspondant, ou None si code invalide
    """
    if letter_code is None or letter_code == 27:  # 27 = zevel/noise
        return None
    
    # Le code 0 correspond à la lettre hébraïque à l'unicode 1488 (א)
    if 0 <= letter_code <= 29:
        return chr(letter_code + 1488)
    
    return None

