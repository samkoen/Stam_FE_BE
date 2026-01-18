"""
Script de visualisation interactive pour la détection des contours.
Ce script utilise le code du serveur (contour_detector) avec show_images=True
pour afficher les différentes étapes de l'algorithme.
"""
import os
import sys
import cv2

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# Forcer le rechargement des modules pour éviter les problèmes de cache
import importlib
if 'BE_Model_Cursor.utils.contour_detector' in sys.modules:
    importlib.reload(sys.modules['BE_Model_Cursor.utils.contour_detector'])
if 'BE_Model_Cursor.utils.rectangle_sorter' in sys.modules:
    importlib.reload(sys.modules['BE_Model_Cursor.utils.rectangle_sorter'])

from BE_Model_Cursor.utils.contour_detector import detect_and_order_contours


def main():
    """
    Fonction principale qui visualise les différentes étapes de la détection des contours.
    Utilise le code du serveur avec show_images=True pour afficher les étapes.
    """
    # Fichier de test hardcodé

    #TEST_IMAGE_FILE = 'kouf2.png'
    TEST_IMAGE_FILE = '001.jpg'
    # Charger l'image de test
    test_images_dir = os.path.join(current_dir, 'test_images')
    test_image_path = os.path.join(test_images_dir, TEST_IMAGE_FILE)
    
    if not os.path.exists(test_image_path):
        print(f"Erreur: Image de test non trouvée : {test_image_path}")
        return
    
    test_image = cv2.imread(test_image_path)
    if test_image is None:
        print(f"Erreur: Impossible de charger l'image : {test_image_path}")
        return
    
    print(f"Chargement de l'image: {TEST_IMAGE_FILE}")
    print("Démarrage de la visualisation des étapes de détection des contours...")
    print("(Les imshow seront affichés à chaque étape)")
    print()
    
    # Utiliser le code du serveur avec show_images=True
    # Cela va afficher toutes les étapes et permettre l'interaction à la fin
    ordered_rects = detect_and_order_contours(test_image, min_contour_area=50, show_images=True)
    
    print(f"\nVisualisation terminée.")
    print(f"Nombre total de rectangles détectés: {len(ordered_rects)}")


if __name__ == '__main__':
    main()
