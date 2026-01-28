import cv2
import numpy as np
from typing import List, Union, Tuple, Optional
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine

class RectRefiner:
    """
    Utilitaire pour raffiner les rectangles détectés en utilisant des techniques
    de traitement d'image avancées (Otsu, morphologie verticale).
    Permet de nettoyer le bruit et de séparer les lettres collées.
    """
    
    @staticmethod
    def refine_rect(image: np.ndarray, rect: Union[Tuple[int, int, int, int], RectangleWithLine]) -> List[Union[Tuple[int, int, int, int], RectangleWithLine]]:
        """
        Tente de raffiner un rectangle :
        1. Nettoie le bruit (lignes horizontales, taches)
        2. Sépare les composantes disjointes (lettres collées)
        3. Recalcule les bounding boxes précises
        
        Args:
            image: Image OpenCV complète
            rect: Le rectangle à traiter
            
        Returns:
            Liste de rectangles (1 ou plusieurs si splitting, ou [original] si échec)
        """
        original_return = [rect]
        
        if image is None:
            return original_return
            
        # Récupérer les coordonnées
        is_obj = isinstance(rect, RectangleWithLine)
        x = rect.x if is_obj else rect[0]
        y = rect.y if is_obj else rect[1]
        w = rect.w if is_obj else rect[2]
        h = rect.h if is_obj else rect[3]
        
        # Marges de sécurité pour le crop
        h_img, w_img = image.shape[:2]
        x_crop = max(0, x - 2)
        y_crop = max(0, y - 2)
        w_crop = min(w_img - x_crop, w + 4)
        h_crop = min(h_img - y_crop, h + 4)
        
        crop = image[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop]
        if crop.size == 0:
            return original_return
            
        # Image processing strict
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Seuillage d'Otsu inversé (texte blanc)
        # Otsu est souvent meilleur localement que l'adaptive global
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Ouverture morphologique avec noyau vertical pour supprimer les lignes horizontales
        # On utilise une ligne verticale de 1x5 pixels
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Trouver les nouveaux contours
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return original_return
            
        # Filtrer et ne garder que les contours significatifs
        # Stratégie : Identifier le contour principal (la lettre) et ignorer les petits bruits satellites
        valid_contours = []
        max_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max_area:
                max_area = area
        
        # Seuil d'aire relatif au plus gros élément (la lettre)
        # On ignore tout ce qui est petit bruit (< 15% de la lettre)
        area_threshold = max(15, max_area * 0.15) 
        
        for cnt in contours:
            if cv2.contourArea(cnt) >= area_threshold:
                valid_contours.append(cnt)
                
        if not valid_contours:
            return original_return
            
        # Analyse des contours pour le splitting ou le raffinement
        result_rects = []
        
        # Si plusieurs contours significatifs, vérifier s'ils sont séparables horizontalement
        if len(valid_contours) > 1:
            # Trier par X
            contour_bboxes = []
            for cnt in valid_contours:
                rx, ry, rw, rh = cv2.boundingRect(cnt)
                contour_bboxes.append((rx, ry, rw, rh))
            
            contour_bboxes.sort(key=lambda b: b[0])
            
            # Fusionner les chevauchements horizontaux
            merged_bboxes = []
            if contour_bboxes:
                curr_x, curr_y, curr_w, curr_h = contour_bboxes[0]
                
                for i in range(1, len(contour_bboxes)):
                    next_x, next_y, next_w, next_h = contour_bboxes[i]
                    
                    # Chevauchement ou très proche (max 2px d'écart)
                    if next_x < curr_x + curr_w + 2:
                        # Fusion
                        new_x = min(curr_x, next_x)
                        new_y = min(curr_y, next_y)
                        new_right = max(curr_x + curr_w, next_x + next_w)
                        new_bottom = max(curr_y + curr_h, next_y + next_h)
                        curr_x, curr_y, curr_w, curr_h = new_x, new_y, new_right - new_x, new_bottom - new_y
                    else:
                        merged_bboxes.append((curr_x, curr_y, curr_w, curr_h))
                        curr_x, curr_y, curr_w, curr_h = next_x, next_y, next_w, next_h
                
                merged_bboxes.append((curr_x, curr_y, curr_w, curr_h))
            
            # Si on a bien séparé en plusieurs blocs
            if len(merged_bboxes) > 1:
                for bx, by, bw, bh in merged_bboxes:
                    abs_x = x_crop + bx
                    # On garde Y original du rectangle parent pour stabilité de l'alignement
                    
                    if is_obj:
                        new_r = rect.copy() # Garde line_number, etc.
                        new_r.x = abs_x
                        new_r.w = bw
                        # new_r.detected_letter = None # Reset detected letter as it changes
                        # new_r.color = (0, 255, 0)
                        result_rects.append(new_r)
                    else:
                        result_rects.append((abs_x, y, bw, h))
                
                return result_rects
                
        # Si un seul bloc (ou fusionné en un seul), on calcule la bbox globale
        min_x = w_crop
        # min_y = h_crop
        max_x = 0
        # max_y = 0
        
        found = False
        for cnt in valid_contours:
            found = True
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            min_x = min(min_x, rx)
            # min_y = min(min_y, ry)
            max_x = max(max_x, rx + rw)
            # max_y = max(max_y, ry + rh)
            
        if not found:
            return original_return
            
        new_w = max_x - min_x
        abs_x = x_crop + min_x
        
        # Si la nouvelle largeur est significativement plus petite (< 95% de l'ancienne)
        # on met à jour. 95% est assez sensible pour le nettoyage.
        if new_w < w * 0.95:
            if is_obj:
                new_r = rect.copy()
                new_r.x = abs_x
                new_r.w = new_w
                return [new_r]
            else:
                return [(abs_x, y, new_w, h)]
                
        return original_return

