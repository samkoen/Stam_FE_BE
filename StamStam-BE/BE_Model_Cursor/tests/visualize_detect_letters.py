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

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

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
    print("\n" + "="*80)
    print("RÉSULTATS DE LA COMPARAISON")
    print("="*80)
    print(f"Paracha détectée: {paracha_name}")
    print(f"Texte détecté (longueur: {len(detected_text)}):")
    print(f"  {detected_text[:200]}..." if len(detected_text) > 200 else f"  {detected_text}")
    print()
    
    if not differences:
        print("✓ SUCCÈS: 100% de correspondance!")
        print("Toutes les lettres sont correctes.")
        return
    
    # Compter les différents types de différences
    missing_count = sum(1 for d in differences if d['type'] == 'missing')
    extra_count = sum(1 for d in differences if d['type'] == 'extra')
    wrong_count = sum(1 for d in differences if d['type'] == 'wrong')
    
    print(f"Résumé des différences:")
    print(f"  - Lettres manquantes (חסר): {missing_count}")
    print(f"  - Lettres en plus (מיותר): {extra_count}")
    print(f"  - Lettres fausses (שגוי): {wrong_count}")
    print()
    
    # Afficher les détails par type
    if missing_count > 0:
        print("Lettres manquantes (חסר):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'missing'], 1):
            context_before = diff.get('context_before', '')
            context_after = diff.get('context_after', '')
            text = diff.get('text', '')
            position = diff.get('position', -1)
            print(f"  {i}. Position {position}: '{text}'")
            if context_before or context_after:
                print(f"     Contexte: ...{context_before}[{text}]{context_after}...")
        print()
    
    if extra_count > 0:
        print("Lettres en plus (מיותר):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'extra'], 1):
            text = diff.get('text', '')
            position = diff.get('position', -1)
            print(f"  {i}. Position {position}: '{text}'")
        print()
    
    if wrong_count > 0:
        print("Lettres fausses (שגוי):")
        for i, diff in enumerate([d for d in differences if d['type'] == 'wrong'], 1):
            text = diff.get('text', '')
            expected = diff.get('expected', '')
            position = diff.get('position', -1)
            print(f"  {i}. Position {position}: détecté '{text}', attendu '{expected}'")
        print()


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
        print(f"Erreur: Impossible de charger l'image : {image_path}")
        return None
    
    filename = os.path.basename(image_path)
    
    if show_contours:
        print(f"Chargement de l'image: {filename}")
        print("Démarrage de la visualisation des étapes de détection des contours...")
        print("(Les imshow seront affichés à chaque étape)")
        print()
        
        # Utiliser le code du serveur avec show_images=True
        # Cela va afficher toutes les étapes et permettre l'interaction à la fin
        ordered_rects = detect_and_order_contours(test_image, min_contour_area=50, show_images=True)
        
        print(f"\nVisualisation des contours terminée.")
        print(f"Nombre total de rectangles détectés: {len(ordered_rects)}")
        print()
    
    if debug:
        print("Démarrage de la détection des lettres et comparaison avec la paracha...")
        print("(Tous les logs seront affichés)")
        print()
    
    # Utiliser la même fonction que le serveur
    # detect_letters retourne: (image_base64, paracha_name, detected_text, differences_info, summary)
    img_base64, paracha_name, detected_text, differences_info, summary = detect_letters(
        test_image, 
        debug=debug
    )
    
    if debug:
        print(f"\nDétection des lettres terminée.")
        print()
    
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
    # Fichier de test hardcodé
    TEST_IMAGE_FILE = 'mezuza1.jpg'
    #TEST_IMAGE_FILE = 'vehaya_avec_un_mot_en_plus.jpg'

    
    # Charger l'image de test
    test_images_dir = os.path.join(current_dir, 'test_images')
    test_image_path = os.path.join(test_images_dir, TEST_IMAGE_FILE)
    
    if not os.path.exists(test_image_path):
        print(f"Erreur: Image de test non trouvée : {test_image_path}")
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
        print(f"Image avec rectangles colorés sauvegardée: {output_path}")
        print("(Vert = correct, Bleu = lettre en plus, Orange = lettre fausse, Rouge = lettre manquante)")


if __name__ == '__main__':
    main()

