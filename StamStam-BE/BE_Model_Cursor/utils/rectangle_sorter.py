"""
Module pour ordonner les rectangles de droite à gauche et de haut en bas
(ordre de lecture hébraïque)
"""
import math
from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine


def follow_rect(self_rect, let_rect, width_mean):
    """
    Vérifie si self_rect peut suivre let_rect sur la même ligne (pour l'ordre hébreu de droite à gauche).
    Copie exacte de la logique Letter.follow().

    Args:
        self_rect: Tuple (x, y, w, h) du rectangle courant (équivalent à self dans Letter.follow)
        let_rect: Tuple (x, y, w, h) du rectangle de référence (équivalent à let dans Letter.follow)
        width_mean: Largeur moyenne des rectangles

    Returns:
        float: Hauteur de chevauchement si les rectangles sont sur la même ligne, None sinon
    """
    # Calculer le chevauchement vertical (même logique que Letter.follow)
    s = max(self_rect[1], let_rect[1])
    h = min(self_rect[1] + self_rect[3], let_rect[1] + let_rect[3]) - s
    
    # Condition exacte de Letter.follow:
    # ((self._chr==12 and h > 5) or (self._chr!=12 and h > 1)) and 
    # (let.rect[0] - (self.rect[0]+self.rect[2])) < widht_mean*8
    # On simplifie en utilisant h > 1 (car on n'a pas accès à _chr)
    # 
    # IMPORTANT: h doit être > 0 pour qu'il y ait un chevauchement vertical réel
    # Si h <= 0, les rectangles ne se chevauchent pas verticalement du tout
    
    # Vérification supplémentaire: s'assurer que les rectangles sont vraiment sur la même ligne
    # en vérifiant que la différence de y n'est pas trop grande
    # Utiliser une tolérance basée sur la hauteur moyenne pour gérer les lettres avec des parties hautes/basses
    height_mean = (self_rect[3] + let_rect[3]) / 2
    y_diff = abs(self_rect[1] - let_rect[1])
    
    # Si la différence de y est trop grande (plus de 1.5 fois la hauteur moyenne), 
    # les rectangles ne sont probablement pas sur la même ligne
    # Mais on permet un chevauchement vertical significatif (au moins 30% de la hauteur moyenne)
    if h > 1 and (let_rect[0] - (self_rect[0] + self_rect[2])) < width_mean * 8:
        # Vérifier que le chevauchement vertical est significatif par rapport à la hauteur
        # ou que les y sont proches
        if h > 0.3 * height_mean or y_diff < 0.5 * height_mean:
            return h
    return None


def is_rect_included(rect_a, rect_b):
    """
    Vérifie si rect_b est entièrement inclus dans rect_a.
    Copie exacte de is_include dans rect_util.py.

    Args:
        rect_a: Tuple (x, y, w, h) du rectangle englobant (équivalent à let_1)
        rect_b: Tuple (x, y, w, h) du rectangle à vérifier (équivalent à let_2)

    Returns:
        bool: True si rect_b est inclus dans rect_a
    """
    # Copie exacte de: a[0] <= b[0] and b[0]+b[2] <= a[0] + a[2] and a[1] <= b[1] and b[1] + b[3] <= a[1] + a[3]
    return (rect_a[0] <= rect_b[0] and rect_b[0] + rect_b[2] <= rect_a[0] + rect_a[2] and
            rect_a[1] <= rect_b[1] and rect_b[1] + rect_b[3] <= rect_a[1] + rect_a[3])


def sort_rectangles_by_lines(rects, debug=False, image=None):
    """
    Ordonne les rectangles en lignes (de droite à gauche dans chaque ligne, 
    puis de haut en bas pour les lignes).

    Inspiré exactement de sort_contour dans letter_separation.py.

    Args:
        rects: Liste de tuples (x, y, w, h) représentant les rectangles
        debug: Si True, affiche des informations de debug
        image: Image pour le debug visuel (optionnel)

    Returns:
        list: Liste ordonnée des rectangles (de droite à gauche, haut en bas)
    """
    flat_list, _ = _sort_rectangles_by_lines_with_lines(rects, debug, image)
    return flat_list


def _sort_rectangles_by_lines_with_lines(rects, debug=False, image=None):
    """
    Version de sort_rectangles_by_lines qui retourne aussi les lignes pour le debug.
    
    Returns:
        tuple: (flat_list, lines) où flat_list est la liste aplatie et lines est la liste des lignes
    """
    if not rects:
        return [], []

    # Helper pour extraire les coordonnées
    def get_coords(r):
        if isinstance(r, RectangleWithLine):
            return r.x, r.y, r.w, r.h
        return r[0], r[1], r[2], r[3]

    # Calculer la largeur et hauteur moyenne globale
    width_mean = sum(get_coords(r)[2] for r in rects) / len(rects) if rects else 50
    height_mean_global = sum(get_coords(r)[3] for r in rects) / len(rects) if rects else 20

    if debug:
        print(f"\n=== DEBUG ORDONNANCEMENT (Étape 7 - Algo A avec Tolérance Petite Lettre) ===")
        print(f"Nombre de rectangles à trier: {len(rects)}")
        print(f"Largeur moyenne: {width_mean:.2f}, Hauteur moyenne: {height_mean_global:.2f}")

    # Trier par position x décroissante (de droite à gauche)
    sorted_rects = sorted(rects, key=lambda r: get_coords(r)[0] + get_coords(r)[2], reverse=True)

    if debug:
        print(f"\nRectangles triés initialement (droite à gauche):")
        for idx, rect in enumerate(sorted_rects[:5]):  # Afficher les 5 premiers
            c = get_coords(rect)
            print(f"  [{idx}] x={c[0]}, y={c[1]}, w={c[2]}, h={c[3]} (x_fin={c[0]+c[2]})")

    # Grouper en lignes
    lines = [[sorted_rects[0]]]  # Première ligne avec le premier rectangle
    skipped_rects = [] # Pour stocker les rectangles rejetés par l'Algo A

    if debug:
        c = get_coords(sorted_rects[0])
        print(f"\nDébut du groupement en lignes...")
        print(f"  -> Ligne 0 créée avec le premier rectangle (x={c[0]}, y={c[1]})")

    # Fonction helper pour trouver le suivant
    def find_next_in_sequence(start_rect, candidates):
        c_start = get_coords(start_rect)
        for cand in candidates:
            c_cand = get_coords(cand)
            if follow_rect(c_cand, c_start, width_mean):
                return cand
        return None

    for i in range(1, len(sorted_rects)):
        current_rect = sorted_rects[i]
        c_curr = get_coords(current_rect)
        
        follow_candidates = []
        last_idx = -1

        if debug:
            print(f"\nTraitement Rectangle {i}: x={c_curr[0]}, y={c_curr[1]}, w={c_curr[2]}, h={c_curr[3]}")

        # Recherche standard
        while len(follow_candidates) == 0 and last_idx > -3:
            line_idx = 0
            for current_line in lines:
                if len(current_line) < abs(last_idx):
                    line_idx += 1
                    continue

                last_rect_in_line = current_line[last_idx]
                c_last = get_coords(last_rect_in_line)
                
                h_overlap = follow_rect(c_curr, c_last, width_mean)

                if debug:
                    s = max(c_curr[1], c_last[1])
                    h_calc = min(c_curr[1] + c_curr[3], c_last[1] + c_last[3]) - s
                    dist_horiz = c_last[0] - (c_curr[0] + c_curr[2])
                    
                    if h_overlap:
                        print(f"    -> MATCH POSSIBLE avec Ligne {line_idx} (rect idx {last_idx}): h_overlap={h_overlap:.2f}")
                    else:
                        print(f"    -> ÉCHEC MATCH Ligne {line_idx} (last={c_last}): h={h_calc:.1f}, dist={dist_horiz:.1f}")

                if h_overlap:
                    follow_candidates.append((current_rect, h_overlap, line_idx, last_rect_in_line))

                line_idx += 1
            last_idx = last_idx - 1

        if len(follow_candidates) == 0:
            # --- ALGO A: Vérification ---
            if debug:
                print(f"  -> Tentative création Nouvelle Ligne. Vérification Algo A...")
            
            potential_followers = sorted_rects[i+1:]
            
            r2 = find_next_in_sequence(current_rect, potential_followers)
            is_valid_starter = True
            
            if r2:
                try:
                    r2_idx = sorted_rects.index(r2)
                    potential_followers_r3 = sorted_rects[r2_idx+1:]
                    r3 = find_next_in_sequence(r2, potential_followers_r3)
                    
                    if r3:
                        c_r1 = get_coords(current_rect)
                        c_r3 = get_coords(r3)
                        
                        consistency = follow_rect(c_r3, c_r1, width_mean)
                        
                        if debug:
                            print(f"    -> R1->R2->R3 trouvé. Consistance R1->R3: {consistency}")
                            
                        if not consistency:
                            # Assouplissement: si R3 est petit (lettre basse/haute, cantillation...), on ne rejette pas
                            if c_r3[3] < height_mean_global * 0.6:
                                if debug:
                                    print(f"    -> Incohérence R1->R3 ignorée car R3 est petit (h={c_r3[3]:.1f})")
                            else:
                                is_valid_starter = False
                                if debug:
                                    print(f"    -> ⚠ ALGO A DÉCLENCHÉ: Incohérence détectée entre R1 (index {i}) et R3.")
                                    print(f"    -> R1 est rejeté. Le rectangle suivant deviendra probablement le nouveau 1er de la ligne.")
                    else:
                        if debug:
                            print(f"    -> R2 trouvé mais pas R3. Starter accepté.")
                except ValueError:
                    pass
            else:
                 if debug:
                    print(f"    -> Pas de R2 trouvé. Starter accepté.")
            
            if is_valid_starter:
                if debug:
                    print(f"  -> AUCUN MATCH. Nouvelle ligne créée (Ligne {len(lines)})")
                lines.append([current_rect])
            else:
                skipped_rects.append(current_rect)
                if debug:
                    print(f"  -> Rectangle ajouté à skipped_rects.")
        else:
            best_match = max(follow_candidates, key=lambda f: f[1])
            line_idx = best_match[2]
            
            if debug:
                print(f"  -> AJOUTÉ à la Ligne {line_idx}")
            
            try:
                check_rect = lines[line_idx][-1]
                if not is_rect_included(check_rect, current_rect):
                    lines[line_idx].append(current_rect)
                else:
                    if debug:
                        print(f"  -> IGNORÉ (inclus)")
            except Exception as e:
                lines.append([current_rect])

    # Ajouter les rejetés
    for skipped in skipped_rects:
        lines.append([skipped])

    # Trier les lignes
    lines.sort(key=lambda line: get_coords(line[0])[1])

    if debug:
        print(f"\n=== RÉSULTAT FINAL ===")
        print(f"Nombre de lignes formées: {len(lines)}")
        for i, line in enumerate(lines):
            first = get_coords(line[0])
            last = get_coords(line[-1])
            print(f"Ligne {i}: {len(line)} rects. Start(x={first[0]}, y={first[1]}) -> End(x={last[0]})")

    # Aplatir
    flat_list = []
    text_position = 0
    for line_idx, line in enumerate(lines):
        for rect in line:
            c = get_coords(rect)
            if isinstance(rect, RectangleWithLine):
                rect_with_line = RectangleWithLine(rect.x, rect.y, rect.w, rect.h, line_idx, rect.detected_letter, text_position, rect.color)
            else:
                rect_with_line = RectangleWithLine(c[0], c[1], c[2], c[3], line_idx, None, text_position)
            flat_list.append(rect_with_line)
            text_position += 1

    return flat_list, lines
