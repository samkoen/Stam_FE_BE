"""
Script de visualisation et test pour la détection complète des lettres (simule "זהה אותיות").
Ce script utilise le code du serveur (letter_detection) avec show_images=True
pour afficher les différentes étapes de l'algorithme et les résultats de la comparaison.
"""
import os
import sys
import cv2
import base64
import numpy as np
import logging

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# Maintenant on peut importer depuis BE_Model_Cursor
from BE_Model_Cursor.utils.logger import StamStamLogger

# Configurer le logger global
logger = StamStamLogger.setup_logger("visualize_detect_letters", level="DEBUG", debug=True)
# S'assurer que les loggers du backend sont aussi en DEBUG
logging.getLogger("BE_Model_Cursor").setLevel(logging.DEBUG)

# Forcer le rechargement des modules pour éviter les problèmes de cache
import importlib
if 'BE_Model_Cursor.letter_detection' in sys.modules:
    importlib.reload(sys.modules['BE_Model_Cursor.letter_detection'])
if 'BE_Model_Cursor.utils.contour_detector' in sys.modules:
    importlib.reload(sys.modules['BE_Model_Cursor.utils.contour_detector'])

from BE_Model_Cursor.utils.contour_detector import detect_and_order_contours
from BE_Model_Cursor.letter_detection import detect_letters


def display_comparison_results(differences, detected_text, paracha_name):
    """
    Affiche les résultats de la comparaison lettre par lettre.
    
    Args:
        differences: Liste des différences trouvées (comme retourné par detect_letters)
        detected_text: Texte détecté
        paracha_name: Nom de la paracha détectée
    """
    logger.info("="*80)
    logger.info("RÉSULTATS DE LA COMPARAISON")
    logger.info("="*80)
    logger.info(f"Paracha détectée: {paracha_name}")
    logger.info(f"Texte détecté (longueur: {len(detected_text)}):")
    logger.info(f"  {detected_text[:200]}..." if len(detected_text) > 200 else f"  {detected_text}")
    
    if not differences:
        logger.info("✓ SUCCÈS: 100% de correspondance!")
        logger.info("Toutes les lettres sont correctes.")
        return
    
    # Compter les différents types de différences
    missing_count = sum(1 for d in differences if d['type'] == 'missing')
    extra_count = sum(1 for d in differences if d['type'] == 'extra')
    wrong_count = sum(1 for d in differences if d['type'] == 'wrong')
    
    logger.info(f"Résumé des différences:")
    logger.info(f"  - Lettres manquantes (חסר): {missing_count}")
    logger.info(f"  - Lettres en plus (מיותר): {extra_count}")
    logger.info(f"  - Lettres fausses (שגוי): {wrong_count}")
    
    # Afficher les détails par type
    if missing_count > 0:
        logger.info("Lettres manquantes (חסר):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'missing'], 1):
            context_before = diff.get('context_before', '')
            context_after = diff.get('context_after', '')
            text = diff.get('text', '')
            position = diff.get('position', -1)
            logger.info(f"  {i}. Position {position}: '{text}'")
            if context_before or context_after:
                logger.info(f"     Contexte: ...{context_before}[{text}]{context_after}...")
    
    if extra_count > 0:
        logger.info("Lettres en plus (מיותר):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'extra'], 1):
            text = diff.get('text', '')
            position = diff.get('position', -1)
            logger.info(f"  {i}. Position {position}: '{text}'")
    
    if wrong_count > 0:
        logger.info("Lettres fausses (שגוי):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'wrong'], 1):
            text = diff.get('text', '')
            expected = diff.get('expected', '')
            position = diff.get('position', -1)
            logger.info(f"  {i}. Position {position}: détecté '{text}', attendu '{expected}'")


def process_single_image(image_path, show_contours=True, debug=True, save_result=False):
    """
    Traite une seule image et retourne les résultats de détection.
    Cette fonction peut être utilisée par visualize_detect_letters et regression_paracha_cacher.
    
    Args:
        image_path: Chemin vers l'image à traiter
        show_contours: Si True, affiche les étapes de détection des contours (imshow)
        debug: Si True, active les logs détaillés
        save_result: Si True, sauvegarde l'image résultante
        
    Returns:
        tuple: (image_base64, paracha_name, detected_text, differences_info, result_image)
               ou None si erreur
    """
    # Charger l'image
    test_image = cv2.imread(image_path)
    if test_image is None:
        logger.error(f"Erreur: Impossible de charger l'image : {image_path}")
        return None
    
    filename = os.path.basename(image_path)
    
    if show_contours:
        logger.info(f"Chargement de l'image: {filename}")
        logger.info("Démarrage de la visualisation des étapes de détection des contours...")
        logger.info("(Les imshow seront affichés à chaque étape)")
        
        # Utiliser le code du serveur avec show_images=True
        # Cela va afficher toutes les étapes et permettre l'interaction à la fin
        ordered_rects = detect_and_order_contours(test_image, min_contour_area=50, show_images=True)
        
        logger.info(f"\nVisualisation des contours terminée.")
        logger.info(f"Nombre total de rectangles détectés: {len(ordered_rects)}")
    
    if debug:
        logger.info("Démarrage de la détection des lettres et comparaison avec la paracha...")
        logger.info("(Tous les logs seront affichés)")
    
    # Utiliser la même fonction que le serveur
    # detect_letters retourne: (image_base64, paracha_name, detected_text, differences_info, summary)
    img_base64, paracha_name, detected_text, differences_info, summary = detect_letters(
        test_image, 
        debug=debug
    )
    
    if debug:
        logger.info(f"\nDétection des lettres terminée.")
    
    # Décoder l'image résultante si nécessaire
    result_image = None
    if save_result or show_contours:
        img_bytes = base64.b64decode(img_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        result_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    return img_base64, paracha_name, detected_text, differences_info, summary, result_image


def main():
    """
    Fonction principale qui visualise les différentes étapes de la détection des lettres
    et compare avec la paracha. Utilise le code du serveur avec show_images=True pour afficher les étapes.
    """
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Fichier de test hardcodé
    #TEST_IMAGE_FILE = '009.jpg'
    TEST_IMAGE_FILE = 'mezuza_mot_en_plus.jpg'

    
    # Charger l'image de test
    test_images_dir = os.path.join(current_dir, 'test_images')
    test_image_path = os.path.join(test_images_dir, TEST_IMAGE_FILE)
    
    if not os.path.exists(test_image_path):
        logger.error(f"Erreur: Image de test non trouvée : {test_image_path}")
        return
    
    # Utiliser la fonction partagée
    result = process_single_image(
        test_image_path, 
        show_contours=True, 
        debug=True, 
        save_result=True
    )
    
    if result is None:
        return
    
    img_base64, paracha_name, detected_text, differences_info, summary, result_image = result
    
    # Afficher les résultats de la comparaison
    display_comparison_results(differences_info, detected_text, paracha_name)
    
    # Sauvegarder l'image avec les rectangles colorés
    if result_image is not None:
        output_path = os.path.join(test_images_dir, f"result_{TEST_IMAGE_FILE}")
        cv2.imwrite(output_path, result_image)
        logger.info(f"Image avec rectangles colorés sauvegardée: {output_path}")
        logger.info("(Vert = correct, Bleu = lettre en plus, Orange = lettre fausse, Rouge = lettre manquante)")


if __name__ == '__main__':
    main()
