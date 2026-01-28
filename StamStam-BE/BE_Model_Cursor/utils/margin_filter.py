import numpy as np
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine

def filter_margin_noise(rects, codes, image_shape, logger=None):
    """
    Filtre les rectangles qui sont probablement du bruit dans les marges.
    Se base sur l'alignement à droite (hébreu) et la cohérence globale du bloc de texte.
    
    Args:
        rects: Liste de rectangles (tuples ou RectangleWithLine)
        codes: Liste des codes de lettres associés
        image_shape: Shape de l'image (height, width)
        logger: Logger optionnel pour le debug
        
    Returns:
        (filtered_rects, filtered_codes)
    """
    if not rects:
        return rects, codes
        
    height, width = image_shape[:2]
    
    # Récupérer les coordonnées de droite (x+w) pour l'alignement à droite
    right_coords = []
    # Récupérer les coordonnées de gauche (x) pour l'alignement à gauche
    left_coords = []
    # Récupérer les coordonnées verticales
    top_coords = []
    bottom_coords = []
    
    for r in rects:
        if isinstance(r, RectangleWithLine):
            right_coords.append(r.x + r.w)
            left_coords.append(r.x)
            top_coords.append(r.y)
            bottom_coords.append(r.y + r.h)
        else:
            right_coords.append(r[0] + r[2])
            left_coords.append(r[0])
            top_coords.append(r[1])
            bottom_coords.append(r[1] + r[3])
            
    if not right_coords:
        return rects, codes
        
    # Utiliser les percentiles pour définir les limites du bloc de texte
    # Cela permet de gérer les mises en page multi-colonnes mieux que la médiane
    
    # Le bord droit "légitime" est défini par le 95e percentile (la quasi-totalité du texte est à gauche de ça)
    right_limit_ref = np.percentile(right_coords, 95)
    
    # Le bord gauche "légitime" est défini par le 5e percentile
    left_limit_ref = np.percentile(left_coords, 5)
    
    # Limites verticales
    top_limit_ref = np.percentile(top_coords, 2) # 2% pour laisser passer les accents/points hauts
    bottom_limit_ref = np.percentile(bottom_coords, 98) # 98%
    
    # Seuils de tolérance (en pixels) pour capturer les éléments un peu hors normes mais valides
    # On permet de dépasser un peu les percentiles.
    # Augmentation à 10% pour éviter de couper les débuts de ligne légitimes un peu décalés ou les en-têtes
    tolerance_w = width * 0.10 # 10% de la largeur
    tolerance_h = height * 0.10 # 10% de la hauteur
    
    filtered_rects = []
    filtered_codes = []
    removed_count = 0
    
    for i, (rect, code) in enumerate(zip(rects, codes)):
        if isinstance(rect, RectangleWithLine):
            x, y, w, h = rect.x, rect.y, rect.w, rect.h
        else:
            x, y, w, h = rect[0], rect[1], rect[2], rect[3]
            
        x_right = x + w
        y_bottom = y + h
        
        # Vérifier marge droite (trop à droite par rapport au bloc global)
        if x_right > right_limit_ref + tolerance_w:
            removed_count += 1
            if logger:
                logger.debug(f"Rect {i} filtré (marge droite): x_right={x_right}, limit={right_limit_ref}")
            continue
            
        # Vérifier marge gauche (trop à gauche par rapport au bloc global)
        if x < left_limit_ref - tolerance_w:
            removed_count += 1
            if logger:
                logger.debug(f"Rect {i} filtré (marge gauche): x={x}, limit={left_limit_ref}")
            continue
            
        # Vérifier marge haut (trop haut par rapport au bloc global)
        if y < top_limit_ref - tolerance_h:
            removed_count += 1
            if logger:
                logger.debug(f"Rect {i} filtré (marge haut): y={y}, limit={top_limit_ref}")
            continue

        # Vérifier marge bas (trop bas par rapport au bloc global)
        if y_bottom > bottom_limit_ref + tolerance_h:
            removed_count += 1
            if logger:
                logger.debug(f"Rect {i} filtré (marge bas): y_bottom={y_bottom}, limit={bottom_limit_ref}")
            continue
                 
        filtered_rects.append(rect)
        filtered_codes.append(code)
        
    if logger and removed_count > 0:
        logger.info(f"Filtre marges: {removed_count} rectangles supprimés (limites: x[{left_limit_ref:.0f}-{right_limit_ref:.0f}], y[{top_limit_ref:.0f}-{bottom_limit_ref:.0f}])")
        
    return filtered_rects, filtered_codes

