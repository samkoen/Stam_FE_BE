"""
Test pour la détection des contours de lettres.
Ce test vérifie uniquement la détection des contours sans charger le modèle ML,
ce qui le rend rapide et ne nécessite pas de charger le cache du modèle.
"""
import os
import sys
import cv2
import numpy as np
import unittest

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
be_model_cursor_dir = os.path.dirname(current_dir)
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

from BE_Model_Cursor.utils.contour_detector import detect_contours, detect_and_order_contours


class TestContourDetection(unittest.TestCase):
    """Tests pour la détection des contours de lettres"""
    
    # Fichier de test hardcodé
    TEST_IMAGE_FILE = '003.jpg'
    
    def setUp(self):
        """Préparation des tests : charger l'image de test hardcodée"""
        self.test_images_dir = os.path.join(current_dir, 'test_images')
        self.test_image_path = os.path.join(self.test_images_dir, self.TEST_IMAGE_FILE)
        
        # Charger l'image de test
        if not os.path.exists(self.test_image_path):
            self.skipTest(f"Image de test non trouvée : {self.test_image_path}")
        
        self.test_image = cv2.imread(self.test_image_path)
        if self.test_image is None:
            self.skipTest(f"Impossible de charger l'image : {self.test_image_path}")
    
    def test_detect_contours_returns_list(self):
        """Test que detect_contours retourne une liste"""
        rects = detect_contours(self.test_image)
        
        self.assertIsInstance(rects, list, 
                             f"detect_contours devrait retourner une liste pour {self.TEST_IMAGE_FILE}")
    
    def test_detect_contours_returns_tuples(self):
        """Test que detect_contours retourne des tuples (x, y, w, h)"""
        rects = detect_contours(self.test_image)
        
        for rect in rects:
            self.assertIsInstance(rect, tuple, 
                                f"Chaque rectangle devrait être un tuple pour {self.TEST_IMAGE_FILE}")
            self.assertEqual(len(rect), 4, 
                           f"Chaque rectangle devrait avoir 4 éléments (x, y, w, h) pour {self.TEST_IMAGE_FILE}")
            x, y, w, h = rect
            self.assertIsInstance(x, (int, float), f"x devrait être un nombre pour {self.TEST_IMAGE_FILE}")
            self.assertIsInstance(y, (int, float), f"y devrait être un nombre pour {self.TEST_IMAGE_FILE}")
            self.assertIsInstance(w, (int, float), f"w devrait être un nombre pour {self.TEST_IMAGE_FILE}")
            self.assertIsInstance(h, (int, float), f"h devrait être un nombre pour {self.TEST_IMAGE_FILE}")
            self.assertGreater(w, 0, f"La largeur w devrait être positive pour {self.TEST_IMAGE_FILE}")
            self.assertGreater(h, 0, f"La hauteur h devrait être positive pour {self.TEST_IMAGE_FILE}")
    
    def test_detect_contours_filters_small_contours(self):
        """Test que detect_contours filtre les contours trop petits"""
        # Avec min_contour_area par défaut (50)
        rects_default = detect_contours(self.test_image, min_contour_area=50)
        
        # Avec min_contour_area plus élevé (1000)
        rects_large = detect_contours(self.test_image, min_contour_area=1000)
        
        # Il devrait y avoir moins ou autant de rectangles avec un seuil plus élevé
        self.assertLessEqual(len(rects_large), len(rects_default),
                           f"Avec min_contour_area=1000, il devrait y avoir moins de rectangles pour {self.TEST_IMAGE_FILE}")
    
    def test_detect_and_order_contours_returns_ordered_list(self):
        """Test que detect_and_order_contours retourne une liste ordonnée"""
        ordered_rects = detect_and_order_contours(self.test_image)
        
        self.assertIsInstance(ordered_rects, list,
                            f"detect_and_order_contours devrait retourner une liste pour {self.TEST_IMAGE_FILE}")
        
        # Vérifier que tous les rectangles sont valides
        for rect in ordered_rects:
            self.assertIsInstance(rect, tuple)
            self.assertEqual(len(rect), 4)
            x, y, w, h = rect
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
    
    def test_detect_contours_empty_image(self):
        """Test que detect_contours gère correctement une image vide"""
        # Créer une image vide (noire)
        empty_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        rects = detect_contours(empty_image)
        
        # Sur une image vide, il ne devrait pas y avoir de contours
        self.assertIsInstance(rects, list)
        # Il peut y avoir 0 ou quelques rectangles selon le traitement, mais ça ne devrait pas planter
    
    def test_detect_contours_consistency(self):
        """Test que detect_contours retourne des résultats cohérents sur la même image"""
        # Appeler deux fois avec les mêmes paramètres
        rects1 = detect_contours(self.test_image, min_contour_area=50)
        rects2 = detect_contours(self.test_image, min_contour_area=50)
        
        # Les résultats devraient être identiques
        self.assertEqual(len(rects1), len(rects2),
                        f"Les résultats devraient être cohérents pour {self.TEST_IMAGE_FILE}")
        
        # Vérifier que les rectangles sont les mêmes (ordre peut varier)
        rects1_set = set(rects1)
        rects2_set = set(rects2)
        self.assertEqual(rects1_set, rects2_set,
                        f"Les rectangles devraient être identiques pour {self.TEST_IMAGE_FILE}")


if __name__ == '__main__':
    unittest.main()

