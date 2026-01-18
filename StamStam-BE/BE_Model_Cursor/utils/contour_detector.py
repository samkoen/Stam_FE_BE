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


def _in_same_line(rect1, rect2, width_mean):
    """
    Vérifie si deux rectangles sont sur la même ligne.
    
    Utilise follow_rect() qui implémente la même logique que Letter.follow().
    
    Args:
        rect1: Tuple (x, y, w, h) du premier rectangle (à droite dans l'ordre hébreu)
        rect2: Tuple (x, y, w, h) du deuxième rectangle (à gauche dans l'ordre hébreu)
        width_mean: Largeur moyenne des rectangles
        
    Returns:
        bool: True si les rectangles sont sur la même ligne
    """
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
    for i, rect_a in enumerate(rects):
        is_included_flag = False
        for j, rect_b in enumerate(rects):
            if i != j and is_included(rect_b, rect_a):
                is_included_flag = True
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
    
    cv2.imshow(title, display_image)
    cv2.waitKey(0)


def _draw_rectangles_on_image(image, rects, color=(0, 255, 0), thickness=2):
    """Dessine des rectangles sur une image."""
    result = image.copy()
    for x, y, w, h in rects:
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
    return result


def _show_rectangles_interactive(image, rects, title, step_name, color=(0, 255, 0)):
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
                cv2.putText(final_image, str(current_rect_index + 1), 
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
            x, y, w, h = rects[current_rect_index]
            cv2.rectangle(final_image, (x, y), (x + w, y + h), color, 2)
            cv2.putText(final_image, str(current_rect_index + 1), 
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

def detect_contours(image, min_contour_area=50, show_images=False):
    """
    Détecte les contours de lettres dans une image et retourne les rectangles correspondants.
    
    Cette fonction effectue uniquement la détection des contours sans prédiction des lettres.
    Elle ne nécessite pas de charger le modèle ML, ce qui la rend rapide pour les tests.
    
    Étapes:
    1-5: Traitement de l'image (gris, flou, seuillage, détection contours)
    6: Filtrage des contours par taille
    7: Ordonnancement (tri par lignes)
    8: Suppression des rectangles inclus
    9: Combinaison des chevauchements horizontaux
    
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
    
    # Étape 8 : Suppression des rectangles inclus
    print(f"[detect_contours] Étape 8: Suppression des rectangles inclus...")
    rects_before_removal = len(valid_rects)
    valid_rects = remove_small_included_rects(valid_rects)
    rects_removed = rects_before_removal - len(valid_rects)
    if rects_removed > 0:
        print(f"[detect_contours] Étape 8: {rects_removed} rectangle(s) inclus supprimé(s) ({rects_before_removal} → {len(valid_rects)})")
    if show_images:
        image_no_included = _draw_rectangles_on_image(image, valid_rects, (255, 255, 0), 2)
        _show_image_with_text(image_no_included, "Etape 8: Sans rectangles inclus",
                            ["Etape 8: Apres suppression des rectangles inclus",
                             f"Nombre de rectangles: {len(valid_rects)}",
                             "Appuyez sur une touche pour continuer"])
    
    # Étape 9 : Combinaison des chevauchements horizontaux
    print(f"[detect_contours] Étape 9: Combinaison des chevauchements horizontaux...")
    rects_before_combine = len(valid_rects)
    valid_rects = combine_horizontal_overlaps(valid_rects, debug=show_images)
    rects_combined = rects_before_combine - len(valid_rects)
    if rects_combined > 0:
        print(f"  ✓ {rects_combined} rectangle(s) combiné(s) ({rects_before_combine} → {len(valid_rects)})")
    else:
        print(f"  ✓ Aucune combinaison nécessaire ({len(valid_rects)} rectangles)")
    if show_images:
        _show_rectangles_interactive(image, valid_rects,
                                   "Etape 9: Combinaison des chevauchements",
                                   "Etape 9: Apres combinaison des chevauchements",
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
                                   "Etape 10: Rectangles finaux",
                                   "Etape 10: Rectangles finaux ordonnes",
                                   color=(0, 255, 0))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return ordered_rects
