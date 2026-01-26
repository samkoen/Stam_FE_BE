"""
Module pour la détection des contours de lettres dans une image.

Ce module se concentre uniquement sur la détection et le traitement des contours,
sans inclure la prédiction des lettres (qui nécessite le modèle ML).
"""
import cv2
import numpy as np


# ============================================================================
# Fonctions utilitaires pour les rectangles
# ============================================================================

def union_rect(a, b):
    """Combine deux rectangles en un rectangle englobant."""
    x = min(a[0], b[0])
    y = min(a[1], b[1])
    w = max(a[0] + a[2], b[0] + b[2]) - x
    h = max(a[1] + a[3], b[1] + b[3]) - y
    return (x, y, w, h)


def intersection_rect(a, b):
    """Calcule l'intersection de deux rectangles."""
    x = max(a[0], b[0])
    y = max(a[1], b[1])
    w = min(a[0] + a[2], b[0] + b[2]) - x
    h = min(a[1] + a[3], b[1] + b[3]) - y
    if w < 0 or h < 0:
        return None
    return (x, y, w, h)


def is_included(a, b):
    """Vérifie si le rectangle b est entièrement inclus dans le rectangle a."""
    return (a[0] <= b[0] and b[0] + b[2] <= a[0] + a[2] and
            a[1] <= b[1] and b[1] + b[3] <= a[1] + a[3])


def follow_rect(rect1, rect2, width_mean):
    """
    Vérifie si rect2 suit rect1 sur la même ligne.
    
    Utilisé pour détecter des lettres comme ק qui ont des parties séparées.
    """
    s = max(rect1[1], rect2[1])
    h = min(rect1[1] + rect1[3], rect2[1] + rect2[3]) - s
    if h > 1 and (rect2[0] - (rect1[0] + rect1[2])) < width_mean * 8:
        return h
    return None


def _in_same_line(rect1, rect2, width_mean=None):
    """
    Vérifie si deux rectangles sont sur la même ligne.
    
    Si les rectangles sont des RectangleWithLine, utilise directement line_number.
    Sinon, utilise l'ancienne méthode avec follow_rect() (pour compatibilité).
    
    Args:
        rect1: RectangleWithLine ou tuple (x, y, w, h) du premier rectangle
        rect2: RectangleWithLine ou tuple (x, y, w, h) du deuxième rectangle
        width_mean: Largeur moyenne des rectangles (optionnel, utilisé seulement si rectangles sont des tuples)
        
    Returns:
        bool: True si les rectangles sont sur la même ligne
    """
    from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
    
    # Si les deux rectangles sont des RectangleWithLine, utiliser line_number
    if isinstance(rect1, RectangleWithLine) and isinstance(rect2, RectangleWithLine):
        return rect1.line_number == rect2.line_number
    
    # Sinon, utiliser l'ancienne méthode pour compatibilité
    if width_mean is None:
        # Calculer width_mean si non fourni
        if isinstance(rect1, RectangleWithLine):
            width_mean = rect1.w
        elif isinstance(rect2, RectangleWithLine):
            width_mean = rect2.w
        else:
            width_mean = (rect1[2] + rect2[2]) / 2 if len(rect1) >= 3 and len(rect2) >= 3 else 50
    
    # Extraire les coordonnées si RectangleWithLine
    if isinstance(rect1, RectangleWithLine):
        rect1 = (rect1.x, rect1.y, rect1.w, rect1.h)
    if isinstance(rect2, RectangleWithLine):
        rect2 = (rect2.x, rect2.y, rect2.w, rect2.h)
    
    h_overlap = follow_rect(rect1, rect2, width_mean)
    return h_overlap is not None


# ============================================================================
# Fonctions de traitement des rectangles
# ============================================================================

def combine_horizontal_overlaps(rects, debug=False):
    """
    Combine les rectangles qui se chevauchent beaucoup horizontalement.
    
    Inspiré de is_horizontal_include de fix_issues_box.
    Cette fonction ne combine que les chevauchements qui correspondent vraiment
    à des parties de la même lettre (comme la "patte" du ה ou ק), pas tous les chevauchements.
    
    Args:
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        debug: Si True, affiche des informations de debug
        
    Returns:
        list: Liste de rectangles avec les chevauchements combinés
    """
    if len(rects) < 2:
        return rects
    
    width_mean = sum(r[2] for r in rects) / len(rects) if rects else 50
    
    if debug:
        print(f"\n=== DEBUG COMBINE_HORIZONTAL_OVERLAPS ===")
        print(f"Nombre de rectangles avant: {len(rects)}")
        print(f"Largeur moyenne: {width_mean:.2f}")
    
    i = 0
    result = []
    
    while i < len(rects):
        current = rects[i]
        
        if debug:
            print(f"\nRectangle {i}: x={current[0]}, y={current[1]}, w={current[2]}, h={current[3]}")
        
        # Chercher uniquement dans le rectangle suivant (i+1)
        if i + 1 < len(rects):
            other = rects[i + 1]
            
            if debug:
                print(f"  Comparaison avec rectangle {i+1}: x={other[0]}, y={other[1]}, w={other[2]}, h={other[3]}")
            
            # Calculer le chevauchement horizontal
            x = max(current[0], other[0])
            w = min(current[0] + current[2], other[0] + other[2]) - x
            
            if debug:
                print(f"  Chevauchement horizontal: w={w:.1f}")
            
            if w > 0:
                # Trouver le rectangle le plus petit
                if current[2] < other[2]:
                    small_w = current[2]
                    smaller_is_current = True
                else:
                    small_w = other[2]
                    smaller_is_current = False
                
                if debug:
                    print(f"  Rectangle le plus petit: {'current (i)' if smaller_is_current else 'other (i+1)'}, w={small_w}")
                    print(f"  Ratio chevauchement: {w/small_w*100:.1f}% (seuil: 70%)")
                
                # Si le chevauchement est > 70% de la largeur du plus petit
                if w > 0.7 * small_w:
                    # Vérifier qu'ils sont vraiment sur la même ligne
                    same_line = _in_same_line(current, other, width_mean)
                    
                    if debug:
                        print(f"  Même ligne: {same_line}")
                    
                    if same_line:
                        # Unifier i et i+1 en un seul rectangle
                        old_current = current
                        current = union_rect(current, other)
                        
                        # IMPORTANT: Mettre à jour rects[i] avec le rectangle unifié
                        # car current est une copie locale, pas une référence
                        rects[i] = current
                        
                        if debug:
                            print(f"  -> UNIFICATION: i={i} et i+1={i+1}")
                            print(f"     Avant: i={old_current}, i+1={other}")
                            print(f"     Après: {current}")
                            print(f"     rects[{i}] mis à jour avec le rectangle unifié")
                        
                        # Supprimer i+1 de la liste
                        removed = rects.pop(i + 1)
                        
                        if debug:
                            print(f"     Rectangle {i+1} supprimé de la liste: {removed}")
                        
                        # Ne pas incrémenter i pour vérifier si on peut combiner avec le nouveau i+1
                        continue
                    elif debug:
                        print(f"  -> Pas de combinaison: pas sur la même ligne")
                elif debug:
                    print(f"  -> Pas de combinaison: chevauchement insuffisant ({w/small_w*100:.1f}% < 70%)")
            elif debug:
                print(f"  -> Pas de chevauchement horizontal (w={w})")
        
        if debug:
            print(f"  Ajout du rectangle {i} au résultat: {current}")
        
        result.append(current)
        i += 1
    
    if debug:
        print(f"\nNombre de rectangles après: {len(result)}")
        print(f"=== FIN DEBUG COMBINE_HORIZONTAL_OVERLAPS ===\n")
    
    return result


def remove_small_included_rects(rects):
    """
    Supprime les rectangles qui sont entièrement inclus dans d'autres.
    
    Args:
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        
    Returns:
        list: Liste de rectangles sans les rectangles inclus
    """
    if len(rects) < 2:
        return rects
    
    result = []
    removed_count = 0
    for i, rect_a in enumerate(rects):
        is_included_flag = False
        for j, rect_b in enumerate(rects):
            if i != j and is_included(rect_b, rect_a):
                is_included_flag = True
                print(f"  [Suppression Inclus] Rectangle {i} {rect_a} est inclus dans Rectangle {j} {rect_b} -> SUPPRIMÉ")
                removed_count += 1
                break
        if not is_included_flag:
            result.append(rect_a)
    
    return result


# ============================================================================
# Fonctions d'affichage (utilisées uniquement si show_images=True)
# ============================================================================

def _show_image_with_text(image, title, text_lines=None):
    """
    Affiche une image avec du texte en bas.
    
    Utilisé uniquement si show_images=True.
    """
    display_image = image.copy()
    
    if text_lines:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        line_height = 25
        y_offset = image.shape[0] - (len(text_lines) * line_height) - 10
        
        for i, line in enumerate(text_lines):
            y_pos = y_offset + (i * line_height)
            text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
            cv2.rectangle(display_image, (5, y_pos - 20), (text_size[0] + 15, y_pos + 5), 
                        (0, 0, 0), -1)
            cv2.putText(display_image, line, (10, y_pos), 
                       font, font_scale, (255, 255, 255), font_thickness)
    
    # Créer une fenêtre redimensionnable
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    # Redimensionner pour voir l'image entière (max 1200x800 pour éviter de dépasser l'écran)
    h, w = display_image.shape[:2]
    scale = min(1200 / w, 800 / h)
    if scale < 1:
        cv2.resizeWindow(title, int(w * scale), int(h * scale))
    else:
        cv2.resizeWindow(title, w, h)
        
    cv2.imshow(title, display_image)
    cv2.waitKey(0)


def _draw_rectangles_on_image(image, rects, color=(0, 255, 0), thickness=2):
    """Dessine des rectangles sur une image."""
    result = image.copy()
    for x, y, w, h in rects:
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
    return result


def _show_rectangles_interactive(image, rects, title, step_name, color=(0, 255, 0), labels=None):
    """
    Affiche les rectangles de manière interactive (un par un avec espace).
    
    Contrôles:
    - ESPACE: afficher le rectangle suivant
    - 'n': passer à l'étape suivante (afficher tous les rectangles restants)
    - 'q' ou ESC: quitter
    
    Args:
        image: Image originale
        rects: Liste de rectangles à afficher
        title: Titre de la fenêtre
        step_name: Nom de l'étape (pour le texte)
        color: Couleur des rectangles
        labels: Liste optionnelle de textes à afficher au-dessus de chaque rectangle (au lieu de l'index)
    """
    final_image = image.copy()
    current_rect_index = 0
    
    # Afficher le texte d'instruction (une seule ligne)
    instruction_text = [
        f"{step_name} - ESPACE: suivant | n: etape suivante | q: quitter | {current_rect_index + 1}/{len(rects)}"
    ]
    
    # Afficher l'image initiale avec les instructions
    display_image = final_image.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    line_height = 25
    y_offset = image.shape[0] - (len(instruction_text) * line_height) - 10
    
    for i, line in enumerate(instruction_text):
        y_pos = y_offset + (i * line_height)
        text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
        cv2.rectangle(display_image, (5, y_pos - 20), (text_size[0] + 15, y_pos + 5), 
                    (0, 0, 0), -1)
        cv2.putText(display_image, line, (10, y_pos), 
                   font, font_scale, (255, 255, 255), font_thickness)
    
    # Créer une fenêtre redimensionnable
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    # Redimensionner pour voir l'image entière (max 1200x800 pour éviter de dépasser l'écran)
    h, w = display_image.shape[:2]
    scale = min(1200 / w, 800 / h)
    if scale < 1:
        cv2.resizeWindow(title, int(w * scale), int(h * scale))
    else:
        cv2.resizeWindow(title, w, h)
        
    cv2.imshow(title, display_image)
    
    # Boucle interactive : ajouter les rectangles un par un avec espace
    while current_rect_index < len(rects):
        key = cv2.waitKey(0) & 0xFF
        
        if key == ord('q') or key == 27:  # 'q' ou ESC pour quitter
            break
        elif key == ord('n'):  # 'n' pour passer à l'étape suivante
            # Afficher tous les rectangles restants d'un coup
            while current_rect_index < len(rects):
                x, y, w, h = rects[current_rect_index]
                cv2.rectangle(final_image, (x, y), (x + w, y + h), color, 2)
                
                # Texte à afficher
                if labels and current_rect_index < len(labels):
                    text = str(labels[current_rect_index])
                else:
                    text = str(current_rect_index + 1)
                    
                # Utiliser une police compatible UTF-8 si possible ou s'assurer que l'hébreu est bien géré par OpenCV (souvent problématique)
                # OpenCV putText ne gère pas bien l'hébreu. On affiche le texte tel quel pour l'instant.
                # Pour l'hébreu, il faudrait utiliser PIL. Mais on va supposer que c'est lisible ou en code.
                cv2.putText(final_image, text, 
                           (x, y - 5), font, 0.5, color, 2)
                current_rect_index += 1
            
            # Mettre à jour l'affichage final
            display_image = final_image.copy()
            instruction_text = [
                f"{step_name} - Tous les rectangles affiches - Appuyez sur une touche pour continuer"
            ]
            
            y_offset = image.shape[0] - (len(instruction_text) * line_height) - 10
            for i, line in enumerate(instruction_text):
                y_pos = y_offset + (i * line_height)
                text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
                cv2.rectangle(display_image, (5, y_pos - 20), (text_size[0] + 15, y_pos + 5), 
                            (0, 0, 0), -1)
                cv2.putText(display_image, line, (10, y_pos), 
                           font, font_scale, (255, 255, 255), font_thickness)
            
            cv2.imshow(title, display_image)
            cv2.waitKey(0)
            break
            
        elif key == ord(' '):  # Espace pour ajouter le rectangle suivant
            # Ajouter le rectangle suivant
            current_rect = rects[current_rect_index]
            x, y, w, h = current_rect
            
            # Log les infos du rectangle
            from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
            line_info = ""
            if isinstance(current_rect, RectangleWithLine):
                line_info = f" | Ligne: {current_rect.line_number}"
                if current_rect.detected_letter:
                    line_info += f" | Lettre: {current_rect.detected_letter}"
            
            print(f"[IMSHOW] Rectangle {current_rect_index}: x={x}, y={y}, w={w}, h={h}{line_info}")
            
            cv2.rectangle(final_image, (x, y), (x + w, y + h), color, 2)
            
            # Texte à afficher
            if labels and current_rect_index < len(labels):
                text = str(labels[current_rect_index])
            else:
                text = str(current_rect_index + 1)
                
            cv2.putText(final_image, text, 
                       (x, y - 5), font, 0.5, color, 2)
            
            current_rect_index += 1
            
            # Mettre à jour l'affichage
            display_image = final_image.copy()
            instruction_text = [
                f"{step_name} - ESPACE: suivant | n: etape suivante | q: quitter | {current_rect_index}/{len(rects)}"
            ]
            
            y_offset = image.shape[0] - (len(instruction_text) * line_height) - 10
            for i, line in enumerate(instruction_text):
                y_pos = y_offset + (i * line_height)
                text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
                cv2.rectangle(display_image, (5, y_pos - 20), (text_size[0] + 15, y_pos + 5), 
                            (0, 0, 0), -1)
                cv2.putText(display_image, line, (10, y_pos), 
                           font, font_scale, (255, 255, 255), font_thickness)
            
            cv2.imshow(title, display_image)


# ============================================================================
# Fonctions principales de détection
# ============================================================================

def split_multi_line_rectangles(image, rects, show_images=False):
    """
    Détecte et sépare les rectangles qui couvrent probablement 2 lignes.
    
    Pour chaque rectangle suspect (hauteur > 1.5x la hauteur moyenne), on :
    1. Accentue les contours dans cette région
    2. Re-détecte les contours pour trouver 2 rectangles séparés
    3. Remplace le grand rectangle par les 2 petits rectangles
    
    Args:
        image: Image OpenCV complète (numpy array) en couleur BGR
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        show_images: Si True, affiche les rectangles un par un avec imshow
        
    Returns:
        list: Liste de rectangles avec les rectangles multi-lignes séparés
    """
    if len(rects) < 2:
        return rects
    
    # Calculer la hauteur moyenne
    heights = [r[3] for r in rects]
    height_mean = sum(heights) / len(heights) if heights else 50
    
    # Seuil : un rectangle est suspect s'il est > 1.8x la hauteur moyenne
    suspect_threshold = height_mean * 1.8
    
    print(f"  Hauteur moyenne: {height_mean:.1f}px, seuil suspect: {suspect_threshold:.1f}px")
    
    result_rects = []
    split_count = 0
    
    for rect_idx, rect in enumerate(rects):
        x, y, w, h = rect
        
        # Vérifier si ce rectangle est suspect
        if h > suspect_threshold:
            print(f"  Rectangle {rect_idx} suspect: h={h:.1f}px (>{suspect_threshold:.1f}px)")
            
            # Extraire la région de l'image
            x_safe = max(0, int(x))
            y_safe = max(0, int(y))
            w_safe = min(image.shape[1] - x_safe, int(w))
            h_safe = min(image.shape[0] - y_safe, int(h))
            
            if w_safe > 0 and h_safe > 0:
                region = image[y_safe:y_safe+h_safe, x_safe:x_safe+w_safe]
                
                if region.size > 0:
                    # Accentuer les contours dans cette région
                    gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                    blurred_region = cv2.GaussianBlur(gray_region, (3, 3), 0)
                    
                    # Seuillage adaptatif plus agressif pour accentuer les contours
                    thresh_region = cv2.adaptiveThreshold(
                        blurred_region,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY_INV,
                        7,  # Plus petit pour plus de sensibilité
                        3   # Plus grand pour accentuer
                    )
                    
                    # Morphologie pour accentuer les séparations verticales
                    # Créer un kernel vertical pour accentuer les séparations horizontales
                    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
                    thresh_region = cv2.morphologyEx(thresh_region, cv2.MORPH_CLOSE, kernel_vertical)
                    
                    # Re-détecter les contours dans cette région
                    contours_region, _ = cv2.findContours(thresh_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Filtrer les contours par taille
                    new_rects = []
                    for contour in contours_region:
                        area = cv2.contourArea(contour)
                        if area < 30:  # Seuil plus petit pour détecter les petites lettres
                            continue
                        
                        rx, ry, rw, rh = cv2.boundingRect(contour)
                        
                        # Filtres: w > 5, h > 8, ratio raisonnable
                        if rw > 5 and rh > 8:
                            aspect_ratio = rw / rh if rh > 0 else 0
                            if 0.1 < aspect_ratio < 5.0:
                                # Coordonnées absolues dans l'image complète
                                abs_x = x_safe + rx
                                abs_y = y_safe + ry
                                new_rects.append((abs_x, abs_y, rw, rh))
                    
                    # Si on a trouvé 2 rectangles ou plus, les utiliser
                    if len(new_rects) >= 2:
                        print(f"    → Trouvé {len(new_rects)} rectangles dans la région, remplacement du rectangle original")
                        result_rects.extend(new_rects)
                        split_count += 1
                        
                        if show_images:
                            # Afficher le rectangle original suspect
                            debug_image = image.copy()
                            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 0, 255), 3)  # Rouge pour suspect
                            cv2.putText(debug_image, f"Suspect {rect_idx}", (x, y - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            
                            # Afficher les nouveaux rectangles trouvés
                            for new_idx, (nx, ny, nw, nh) in enumerate(new_rects):
                                cv2.rectangle(debug_image, (nx, ny), (nx + nw, ny + nh), (0, 255, 0), 2)  # Vert pour nouveau
                                cv2.putText(debug_image, f"New {new_idx}", (nx, ny - 5),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            _show_image_with_text(debug_image, f"Etape 8: Rectangle {rect_idx} separe",
                                                [f"Rectangle {rect_idx} suspect (h={h:.1f}px)",
                                                 f"Trouve {len(new_rects)} rectangles dans la region",
                                                 "Appuyez sur une touche pour continuer"])
                            
                            # Afficher les nouveaux rectangles un par un
                            _show_rectangles_interactive(image, new_rects,
                                                       f"Etape 8: Nouveaux rectangles de {rect_idx}",
                                                       f"Etape 8: Nouveaux rectangles trouves dans {rect_idx}",
                                                       color=(0, 255, 0))
                    else:
                        # Pas assez de rectangles trouvés, garder l'original
                        print(f"    → Trouvé seulement {len(new_rects)} rectangle(s), garde l'original")
                        result_rects.append(rect)
                else:
                    # Région invalide, garder l'original
                    result_rects.append(rect)
            else:
                # Coordonnées invalides, garder l'original
                result_rects.append(rect)
        else:
            # Rectangle normal, le garder tel quel
            result_rects.append(rect)
    
    if split_count > 0:
        print(f"  ✓ {split_count} rectangle(s) multi-lignes séparé(s) ({len(rects)} → {len(result_rects)} rectangles)")
    else:
        print(f"  ✓ Aucun rectangle multi-lignes détecté ({len(rects)} rectangles)")
    
    return result_rects


def detect_contours(image, min_contour_area=50, show_images=False):
    """
    Détecte les contours de lettres dans une image et retourne les rectangles correspondants.
    
    Cette fonction effectue uniquement la détection des contours sans prédiction des lettres.
    Elle ne nécessite pas de charger le modèle ML, ce qui la rend rapide pour les tests.
    
    Étapes:
    1-5: Traitement de l'image (gris, flou, seuillage, détection contours)
    6: Filtrage des contours par taille
    7: Ordonnancement (tri par lignes)
    8: Détection et séparation des rectangles multi-lignes
    9: Suppression des rectangles inclus
    10: Combinaison des chevauchements horizontaux
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        min_contour_area: Surface minimale d'un contour pour être considéré (défaut: 50)
        show_images: Si True, affiche les étapes avec imshow (défaut: False)
        
    Returns:
        list: Liste de tuples (x, y, w, h) représentant les rectangles des lettres détectées
    """
    # Étape 1-5 : Traitement de l'image
    print(f"[detect_contours] Étapes 1-5: Traitement de l'image (gris, flou, seuillage, détection contours)...")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
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
    print(f"  ✓ {len(contours)} contours détectés")
    
    # Étape 6 : Filtrage des contours par taille
    print(f"[detect_contours] Étape 6: Filtrage des contours par taille (min_area={min_contour_area})...")
    valid_rects = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_contour_area:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filtres: w > 5, h > 8, w < 1000, ratio raisonnable
        if w > 5 and h > 8 and w < 1000:
            aspect_ratio = w / h if h > 0 else 0
            if 0.1 < aspect_ratio < 5.0:
                valid_rects.append((x, y, w, h))
            else:
                if show_images:
                    print(f"  [Filtrage] Rectangle rejeté (ratio invalide): {w}x{h}, ratio={aspect_ratio:.2f}")
        else:
            if show_images:
                print(f"  [Filtrage] Rectangle rejeté (dimensions hors limites): {w}x{h}")
    
    print(f"  ✓ {len(valid_rects)} rectangles valides après filtrage")
    if show_images:
        image_filtered = _draw_rectangles_on_image(image, valid_rects, (0, 255, 255), 2)
        _show_image_with_text(image_filtered, "Etape 6: Contours filtres",
                            ["Etape 6: Contours filtres par taille",
                             f"Nombre de rectangles: {len(valid_rects)}",
                             "Appuyez sur une touche pour continuer"])
    
    # Étape 7 : Ordonnancement (tri par lignes)
    print(f"[detect_contours] Étape 7: Ordonnancement par lignes...")
    from BE_Model_Cursor.utils.rectangle_sorter import sort_rectangles_by_lines, _sort_rectangles_by_lines_with_lines
    
    if show_images:
        # Utiliser la version qui retourne aussi les lignes pour le debug
        valid_rects, lines = _sort_rectangles_by_lines_with_lines(valid_rects, debug=True, image=image)
        
        # Afficher les lignes avec des couleurs différentes pour le debug
        debug_image = image.copy()
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        for line_idx, line in enumerate(lines):
            color = colors[line_idx % len(colors)]
            for rect in line:
                x, y, w, h = rect
                cv2.rectangle(debug_image, (x, y), (x + w, y + h), color, 2)
                cv2.putText(debug_image, f"L{line_idx}", (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        _show_image_with_text(debug_image, "Etape 7 Debug: Lignes detectees",
                            [f"Etape 7 Debug: {len(lines)} lignes detectees",
                             "Chaque ligne a une couleur differente",
                             "Appuyez sur une touche pour continuer"])
        
        # Puis afficher de manière interactive
        _show_rectangles_interactive(image, valid_rects,
                                   "Etape 7: Ordonnancement",
                                   "Etape 7: Apres ordonnancement par lignes",
                                   color=(255, 0, 255))
        print(f"  ✓ {len(lines)} lignes détectées, {len(valid_rects)} rectangles ordonnés")
    else:
        valid_rects = sort_rectangles_by_lines(valid_rects, debug=False, image=None)
        print(f"  ✓ Ordonnancement terminé: {len(valid_rects)} rectangles")
    
    # Étape 7bis : Suppression des lignes parasites (1 seul élément très petit)
    print(f"[detect_contours] Étape 7bis: Nettoyage des lignes parasites...")
    if len(valid_rects) > 0:
        # Grouper par ligne
        lines_dict = {}
        for r in valid_rects:
            # Gérer RectangleWithLine ou tuple
            if hasattr(r, 'line_number'):
                line_id = r.line_number
            else:
                line_id = 0 # Fallback
            
            if line_id not in lines_dict:
                lines_dict[line_id] = []
            lines_dict[line_id].append(r)
            
        # Calculer la taille moyenne globale et la surface moyenne
        widths = [r.w if hasattr(r, 'w') else r[2] for r in valid_rects]
        heights = [r.h if hasattr(r, 'h') else r[3] for r in valid_rects]
        areas = [(r.w * r.h) if hasattr(r, 'w') else (r[2] * r[3]) for r in valid_rects]
        
        avg_w = sum(widths) / len(widths) if widths else 0
        avg_h = sum(heights) / len(heights) if heights else 0
        avg_area = sum(areas) / len(areas) if areas else 0
        
        print(f"  Moyenne globale: {avg_w:.1f}x{avg_h:.1f} (Surface: {avg_area:.1f})")
        
        rects_to_keep = []
        removed_count = 0
        
        # Parcourir les lignes triées par ID pour garder l'ordre
        for line_id in sorted(lines_dict.keys()):
            line_rects = lines_dict[line_id]
            
            # Vérifier si TOUS les rectangles de la ligne sont petits/parasites
            all_small = True
            for r in line_rects:
                w = r.w if hasattr(r, 'w') else r[2]
                h = r.h if hasattr(r, 'h') else r[3]
                area = w * h
                
                # Critère: Surface < 15% de la moyenne
                # (Les lettres normales font ~7000px, les parasites ~400px soit < 6%)
                # On prend 15% pour être sûr (ex: ~1000px)
                # On ajoute aussi une condition sur la hauteur minimale absolue (ex: < 40px) si la surface est limite
                
                is_small_area = (area < avg_area * 0.15)
                is_small_dim = (w < avg_w * 0.6 and h < avg_h * 0.6)
                
                if not (is_small_area or is_small_dim):
                    all_small = False
                    break
            
            if all_small:
                print(f"  [Nettoyage Lignes] Ligne {line_id} supprimée : contient uniquement {len(line_rects)} petit(s) rectangle(s) parasite(s)")
                removed_count += 1
                continue # On ne l'ajoute pas
            
            rects_to_keep.extend(line_rects)
            
        valid_rects = rects_to_keep
        print(f"  ✓ {removed_count} ligne(s) parasite(s) supprimée(s)")

    # Étape 8 : Détection et séparation des rectangles couvrant 2 lignes
    print(f"[detect_contours] Étape 8: Détection et séparation des rectangles multi-lignes...")
    valid_rects = split_multi_line_rectangles(image, valid_rects, show_images=show_images)
    
    # Réordonner les rectangles après la séparation (car les nouveaux rectangles peuvent être dans un ordre différent)
    if len(valid_rects) > 0:
        from BE_Model_Cursor.utils.rectangle_sorter import sort_rectangles_by_lines
        valid_rects = sort_rectangles_by_lines(valid_rects, debug=False, image=None)
        print(f"  ✓ Rectangles réordonnés après séparation: {len(valid_rects)} rectangles")
    
    # Étape 9 : Suppression des rectangles inclus
    print(f"[detect_contours] Étape 9: Suppression des rectangles inclus...")
    rects_before_removal = len(valid_rects)
    valid_rects = remove_small_included_rects(valid_rects)
    rects_removed = rects_before_removal - len(valid_rects)
    if rects_removed > 0:
        print(f"[detect_contours] Étape 9: {rects_removed} rectangle(s) inclus supprimé(s) ({rects_before_removal} → {len(valid_rects)})")
    if show_images:
        image_no_included = _draw_rectangles_on_image(image, valid_rects, (255, 255, 0), 2)
        _show_image_with_text(image_no_included, "Etape 9: Sans rectangles inclus",
                            ["Etape 9: Apres suppression des rectangles inclus",
                             f"Nombre de rectangles: {len(valid_rects)}",
                             "Appuyez sur une touche pour continuer"])
    
    # Étape 10 : Combinaison des chevauchements horizontaux
    print(f"[detect_contours] Étape 10: Combinaison des chevauchements horizontaux...")
    rects_before_combine = len(valid_rects)
    valid_rects = combine_horizontal_overlaps(valid_rects, debug=show_images)
    rects_combined = rects_before_combine - len(valid_rects)
    if rects_combined > 0:
        print(f"  ✓ {rects_combined} rectangle(s) combiné(s) ({rects_before_combine} → {len(valid_rects)})")
    else:
        print(f"  ✓ Aucune combinaison nécessaire ({len(valid_rects)} rectangles)")
    if show_images:
        _show_rectangles_interactive(image, valid_rects,
                                   "Etape 10: Combinaison des chevauchements",
                                   "Etape 10: Apres combinaison des chevauchements",
                                   color=(0, 255, 255))
    
    return valid_rects


def detect_and_order_contours(image, min_contour_area=50, show_images=False):
    """
    Détecte les contours de lettres dans une image, les traite et les ordonne.
    
    Cette fonction effectue la détection complète des contours avec ordonnancement,
    mais sans prédiction des lettres. Elle ne nécessite pas de charger le modèle ML.
    
    Args:
        image: Image OpenCV (numpy array) en couleur BGR
        min_contour_area: Surface minimale d'un contour pour être considéré (défaut: 50)
        show_images: Si True, affiche les étapes avec imshow (défaut: False)
        
    Returns:
        list: Liste ordonnée de tuples (x, y, w, h) représentant les rectangles des lettres
              détectées, ordonnés de droite à gauche et de haut en bas (ordre hébreu)
    """
    # Détecter les contours (avec affichage des étapes si show_images=True)
    ordered_rects = detect_contours(image, min_contour_area, show_images=show_images)
    
    # Si aucun rectangle valide, retourner une liste vide
    if len(ordered_rects) == 0:
        if show_images:
            cv2.destroyAllWindows()
        return []
    
    # Dernière étape : Affichage interactif avec ajout progressif des rectangles
    if show_images:
        _show_rectangles_interactive(image, ordered_rects,
                                   "Etape 11: Rectangles finaux",
                                   "Etape 11: Rectangles finaux ordonnes (apres toutes les etapes)",
                                   color=(0, 255, 0))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return ordered_rects
