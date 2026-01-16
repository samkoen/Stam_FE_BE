"""
Module pour ordonner les rectangles de droite à gauche et de haut en bas
(ordre de lecture hébraïque)
"""
import math


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
    if not rects:
        return []

    # Calculer la largeur moyenne
    width_mean = sum(r[2] for r in rects) / len(rects) if rects else 50

    if debug:
        print(f"\n=== DEBUG ORDONNANCEMENT ===")
        print(f"Nombre de rectangles: {len(rects)}")
        print(f"Largeur moyenne: {width_mean:.2f}")

    # Trier par position x décroissante (de droite à gauche)
    # Comme dans sort_contour: letters.sort(key=lambda b: b.rect[0]+b.rect[2],reverse=True)
    sorted_rects = sorted(rects, key=lambda r: r[0] + r[2], reverse=True)

    if debug:
        print(f"\nRectangles triés (droite à gauche):")
        for idx, rect in enumerate(sorted_rects[:5]):  # Afficher les 5 premiers
            print(f"  {idx}: x={rect[0]}, y={rect[1]}, w={rect[2]}, h={rect[3]}")

    # Grouper en lignes (comme dans sort_contour)
    lines = [[sorted_rects[0]]]  # Première ligne avec le premier rectangle

    if debug:
        print(f"\nDébut du groupement en lignes...")

    # Copie exacte de la boucle dans sort_contour
    for i in range(1, len(sorted_rects)):
        current_rect = sorted_rects[i]
        follow_candidates = []
        last_idx = -1

        if debug:
            print(f"\nRectangle {i}: x={current_rect[0]}, y={current_rect[1]}, w={current_rect[2]}, h={current_rect[3]}")

        # Copie exacte: while len(follow_letters)==0 and last_idx > -3
        while len(follow_candidates) == 0 and last_idx > -3:
            line_idx = 0
            for current_line in lines:
                # Copie exacte: if len(current_line) < abs(last_idx): continue
                if len(current_line) < abs(last_idx):
                    line_idx += 1
                    continue

                last_rect_in_line = current_line[last_idx]
                # Copie exacte: h = letters[i].follow(last_rect, width_mean)
                # Dans Letter.follow: self=letters[i], let=last_rect
                h_overlap = follow_rect(current_rect, last_rect_in_line, width_mean)

                if debug:
                    # Debug détaillé pour comprendre pourquoi certains rectangles sont mal groupés
                    s = max(current_rect[1], last_rect_in_line[1])
                    h_calc = min(current_rect[1] + current_rect[3], last_rect_in_line[1] + last_rect_in_line[3]) - s
                    dist_horiz = last_rect_in_line[0] - (current_rect[0] + current_rect[2])
                    if h_overlap:
                        print(f"  -> Match avec ligne {line_idx}, dernier rect (idx {last_idx}): "
                              f"x={last_rect_in_line[0]}, y={last_rect_in_line[1]}, "
                              f"h_overlap={h_overlap:.2f}, dist_horiz={dist_horiz:.1f}")
                    elif i < 50:  # Debug pour les 50 premiers rectangles pour voir les non-matchs
                        print(f"  -> Pas de match ligne {line_idx} (idx {last_idx}): "
                              f"h_calc={h_calc:.1f}, dist_horiz={dist_horiz:.1f}, "
                              f"seuil_dist={width_mean*8:.1f}")

                # Copie exacte: if h: follow_letters.append((letters[i], h, line, last_rect))
                if h_overlap:
                    follow_candidates.append((current_rect, h_overlap, line_idx, last_rect_in_line))

                line_idx += 1

            # Copie exacte: last_idx = last_idx - 1
            last_idx = last_idx - 1

        # Copie exacte: if len(follow_letters)==0: lines.append([letters[i]])
        if len(follow_candidates) == 0:
            if debug:
                print(f"  -> Nouvelle ligne créée (ligne {len(lines)})")
            lines.append([current_rect])
        else:
            # Copie exacte: follow_letter = max(follow_letters, key=lambda f: f[1])
            best_match = max(follow_candidates, key=lambda f: f[1])
            line_idx = best_match[2]
            
            if debug:
                print(f"  -> Ajouté à la ligne {line_idx} (h_overlap={best_match[1]:.2f})")
            
            # Copie exacte: 
            # try:
            #     if not is_include(lines[follow_letter[2]][last_idx+1], letters[i]):
            #         lines[follow_letter[2]].append(letters[i])
            #     else:
            #         pass
            # except Exception as e:
            #     pass
            try:
                check_idx = last_idx + 1
                if check_idx < len(lines[line_idx]):
                    check_rect = lines[line_idx][check_idx]
                    if not is_rect_included(check_rect, current_rect):
                        lines[line_idx].append(current_rect)
                    else:
                        if debug:
                            print(f"  -> Ignoré (inclus dans rect de la ligne)")
                        # pass (comme dans l'original)
                else:
                    lines[line_idx].append(current_rect)
            except Exception as e:
                if debug:
                    print(f"  -> Exception: {e}")
                # pass (comme dans l'original, mais on ne crée pas de nouvelle ligne)

    # Trier les lignes de haut en bas (par y croissant du coin supérieur droit)
    # Utiliser le rectangle le plus à droite de chaque ligne (premier dans la liste, déjà trié de droite à gauche)
    # et utiliser son y (coin supérieur droit)
    lines.sort(key=lambda line: line[0][1])  # y du coin supérieur droit du rectangle le plus à droite

    if debug:
        print(f"\n=== RÉSULTAT FINAL ===")
        print(f"Nombre de lignes: {len(lines)}")
        for line_idx, line in enumerate(lines):
            first_rect = line[0]
            top_right_x = first_rect[0] + first_rect[2]
            print(f"Ligne {line_idx} (coin sup droit: x={top_right_x}, y={first_rect[1]}): {len(line)} rectangles")
            for rect_idx, rect in enumerate(line[:3]):  # Afficher les 3 premiers de chaque ligne
                top_right_x_rect = rect[0] + rect[2]
                print(f"  {rect_idx}: coin sup droit (x={top_right_x_rect}, y={rect[1]}), coin inf gauche (x={rect[0]}, y={rect[1]+rect[3]})")

    # Aplatir la liste (les rectangles dans chaque ligne sont déjà de droite à gauche)
    # Comme dans sort_contour: flat_list = [item for sublist in lines for item in sublist]
    flat_list = [rect for line in lines for rect in line]

    return flat_list


def _sort_rectangles_by_lines_with_lines(rects, debug=False, image=None):
    """
    Version de sort_rectangles_by_lines qui retourne aussi les lignes pour le debug.
    
    Returns:
        tuple: (flat_list, lines) où flat_list est la liste aplatie et lines est la liste des lignes
    """
    if not rects:
        return [], []

    # Calculer la largeur moyenne
    width_mean = sum(r[2] for r in rects) / len(rects) if rects else 50

    if debug:
        print(f"\n=== DEBUG ORDONNANCEMENT ===")
        print(f"Nombre de rectangles: {len(rects)}")
        print(f"Largeur moyenne: {width_mean:.2f}")

    # Trier par position x décroissante (de droite à gauche)
    sorted_rects = sorted(rects, key=lambda r: r[0] + r[2], reverse=True)

    if debug:
        print(f"\nRectangles triés (droite à gauche):")
        for idx, rect in enumerate(sorted_rects[:10]):  # Afficher les 10 premiers
            print(f"  {idx}: x={rect[0]}, y={rect[1]}, w={rect[2]}, h={rect[3]}")

    # Grouper en lignes
    lines = [[sorted_rects[0]]]

    if debug:
        print(f"\nDébut du groupement en lignes...")

    for i in range(1, len(sorted_rects)):
        current_rect = sorted_rects[i]
        follow_candidates = []
        last_idx = -1

        if debug and i < 20:  # Debug seulement pour les 20 premiers
            print(f"\nRectangle {i}: x={current_rect[0]}, y={current_rect[1]}, w={current_rect[2]}, h={current_rect[3]}")

        while len(follow_candidates) == 0 and last_idx > -3:
            line_idx = 0
            for current_line in lines:
                if len(current_line) < abs(last_idx):
                    line_idx += 1
                    continue

                last_rect_in_line = current_line[last_idx]
                h_overlap = follow_rect(current_rect, last_rect_in_line, width_mean)

                if debug and i < 20 and h_overlap:
                    print(f"  -> Match avec ligne {line_idx}, dernier rect (idx {last_idx}): "
                          f"x={last_rect_in_line[0]}, y={last_rect_in_line[1]}, "
                          f"h_overlap={h_overlap:.2f}")

                if h_overlap:
                    follow_candidates.append((current_rect, h_overlap, line_idx, last_rect_in_line))

                line_idx += 1

            last_idx -= 1

        if len(follow_candidates) == 0:
            if debug and i < 20:
                print(f"  -> Nouvelle ligne créée (ligne {len(lines)})")
            lines.append([current_rect])
        else:
            best_match = max(follow_candidates, key=lambda f: f[1])
            line_idx = best_match[2]
            
            if debug and i < 20:
                print(f"  -> Ajouté à la ligne {line_idx} (h_overlap={best_match[1]:.2f})")
            
            try:
                check_idx = last_idx + 1
                if check_idx < len(lines[line_idx]):
                    check_rect = lines[line_idx][check_idx]
                    if not is_rect_included(check_rect, current_rect):
                        lines[line_idx].append(current_rect)
                    else:
                        if debug and i < 20:
                            print(f"  -> Ignoré (inclus dans rect de la ligne)")
                else:
                    lines[line_idx].append(current_rect)
            except Exception as e:
                if debug and i < 20:
                    print(f"  -> Exception: {e}")
                lines.append([current_rect])

    # Trier les lignes de haut en bas (par y du coin supérieur droit)
    lines.sort(key=lambda line: line[0][1])

    if debug:
        print(f"\n=== RÉSULTAT FINAL ===")
        print(f"Nombre de lignes: {len(lines)}")
        for line_idx, line in enumerate(lines):
            first_rect = line[0]
            top_right_x = first_rect[0] + first_rect[2]
            print(f"Ligne {line_idx} (coin sup droit: x={top_right_x}, y={first_rect[1]}): {len(line)} rectangles")
            for rect_idx, rect in enumerate(line[:5]):  # Afficher les 5 premiers de chaque ligne
                top_right_x_rect = rect[0] + rect[2]
                print(f"  {rect_idx}: coin sup droit (x={top_right_x_rect}, y={rect[1]}), coin inf gauche (x={rect[0]}, y={rect[1]+rect[3]})")

    flat_list = [rect for line in lines for rect in line]

    return flat_list, lines

