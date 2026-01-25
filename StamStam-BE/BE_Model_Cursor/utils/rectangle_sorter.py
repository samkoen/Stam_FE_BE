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

    # Calculer la largeur moyenne
    # Extraire w si RectangleWithLine, sinon utiliser l'index [2]
    width_mean = sum(r.w if isinstance(r, RectangleWithLine) else r[2] for r in rects) / len(rects) if rects else 50

    if debug:
        print(f"\n=== DEBUG ORDONNANCEMENT (Étape 7) ===")
        print(f"Nombre de rectangles à trier: {len(rects)}")
        print(f"Largeur moyenne des rectangles: {width_mean:.2f}")

    # Trier par position x décroissante (de droite à gauche)
    # Comme dans sort_contour: letters.sort(key=lambda b: b.rect[0]+b.rect[2],reverse=True)
    # Extraire x et w si RectangleWithLine, sinon utiliser les index
    sorted_rects = sorted(rects, key=lambda r: (r.x if isinstance(r, RectangleWithLine) else r[0]) + (r.w if isinstance(r, RectangleWithLine) else r[2]), reverse=True)

    if debug:
        print(f"\nRectangles triés initialement (droite à gauche):")
        for idx, rect in enumerate(sorted_rects[:5]):  # Afficher les 5 premiers
            if isinstance(rect, RectangleWithLine):
                print(f"  [{idx}] x={rect.x}, y={rect.y}, w={rect.w}, h={rect.h} (x_fin={rect.x+rect.w})")
            else:
                print(f"  [{idx}] x={rect[0]}, y={rect[1]}, w={rect[2]}, h={rect[3]} (x_fin={rect[0]+rect[2]})")

    # Grouper en lignes (comme dans sort_contour)
    lines = [[sorted_rects[0]]]  # Première ligne avec le premier rectangle

    if debug:
        print(f"\nDébut du groupement en lignes...")
        if isinstance(sorted_rects[0], RectangleWithLine):
            print(f"  -> Ligne 0 créée avec le premier rectangle (x={sorted_rects[0].x}, y={sorted_rects[0].y})")
        else:
            print(f"  -> Ligne 0 créée avec le premier rectangle (x={sorted_rects[0][0]}, y={sorted_rects[0][1]})")

    # Copie exacte de la boucle dans sort_contour
    for i in range(1, len(sorted_rects)):
        current_rect = sorted_rects[i]
        follow_candidates = []
        last_idx = -1

        if debug:
            if isinstance(current_rect, RectangleWithLine):
                print(f"\nTraitement Rectangle {i}: x={current_rect.x}, y={current_rect.y}, w={current_rect.w}, h={current_rect.h}")
            else:
                print(f"\nTraitement Rectangle {i}: x={current_rect[0]}, y={current_rect[1]}, w={current_rect[2]}, h={current_rect[3]}")

        # Copie exacte: while len(follow_letters)==0 and last_idx > -3
        # On regarde jusqu'à 3 rectangles en arrière dans chaque ligne existante
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
                # Extraire les coordonnées si RectangleWithLine pour follow_rect
                current_rect_tuple = (current_rect.x, current_rect.y, current_rect.w, current_rect.h) if isinstance(current_rect, RectangleWithLine) else current_rect
                last_rect_tuple = (last_rect_in_line.x, last_rect_in_line.y, last_rect_in_line.w, last_rect_in_line.h) if isinstance(last_rect_in_line, RectangleWithLine) else last_rect_in_line
                h_overlap = follow_rect(current_rect_tuple, last_rect_tuple, width_mean)

                if debug:
                    # Debug détaillé pour comprendre pourquoi certains rectangles sont mal groupés
                    # Extraire les coordonnées si RectangleWithLine
                    current_y = current_rect.y if isinstance(current_rect, RectangleWithLine) else current_rect[1]
                    current_h = current_rect.h if isinstance(current_rect, RectangleWithLine) else current_rect[3]
                    current_x = current_rect.x if isinstance(current_rect, RectangleWithLine) else current_rect[0]
                    current_w = current_rect.w if isinstance(current_rect, RectangleWithLine) else current_rect[2]
                    last_y = last_rect_in_line.y if isinstance(last_rect_in_line, RectangleWithLine) else last_rect_in_line[1]
                    last_h = last_rect_in_line.h if isinstance(last_rect_in_line, RectangleWithLine) else last_rect_in_line[3]
                    last_x = last_rect_in_line.x if isinstance(last_rect_in_line, RectangleWithLine) else last_rect_in_line[0]
                    last_w = last_rect_in_line.w if isinstance(last_rect_in_line, RectangleWithLine) else last_rect_in_line[2]
                    s = max(current_y, last_y)
                    h_calc = min(current_y + current_h, last_y + last_h) - s
                    dist_horiz = last_x - (current_x + current_w)

                    if h_overlap:
                        print(f"    -> MATCH POSSIBLE avec Ligne {line_idx} (rect idx {last_idx} depuis la fin):")
                        print(f"       Candidat: x={last_x}, y={last_y}, h_overlap={h_overlap:.2f}, dist_horiz={dist_horiz:.1f}")
                    else:
                        # Expliquer pourquoi ça ne matche pas
                        reason = ""
                        height_mean_pair = (current_h + last_h) / 2
                        y_diff = abs(current_y - last_y)

                        if h_calc <= 1 and not (h_calc > 0.3 * height_mean_pair or y_diff < 0.5 * height_mean_pair):
                            reason = f"Pas assez de chevauchement vertical (h={h_calc:.1f})"
                        elif dist_horiz >= width_mean * 8:
                            reason = f"Trop loin horizontalement (dist={dist_horiz:.1f} >= {width_mean * 8:.1f})"

                        print(f"    -> Pas de match Ligne {line_idx} (rect idx {last_idx}): {reason}")

                # Copie exacte: if h: follow_letters.append((letters[i], h, line, last_rect))
                if h_overlap:
                    follow_candidates.append((current_rect, h_overlap, line_idx, last_rect_in_line))

                line_idx += 1

            # Copie exacte: last_idx = last_idx - 1
            last_idx = last_idx - 1

        # Copie exacte: if len(follow_letters)==0: lines.append([letters[i]])
        if len(follow_candidates) == 0:
            if debug:
                print(f"  -> AUCUN MATCH TROUVÉ. Nouvelle ligne créée (Ligne {len(lines)})")
            lines.append([current_rect])
        else:
            # Copie exacte: follow_letter = max(follow_letters, key=lambda f: f[1])
            best_match = max(follow_candidates, key=lambda f: f[1])
            line_idx = best_match[2]

            if debug:
                print(f"  -> AJOUTÉ à la Ligne {line_idx} (Meilleur chevauchement: {best_match[1]:.2f})")

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
                            print(f"  -> IGNORÉ (car inclus dans un autre rectangle de la ligne)")
                        # pass (comme dans l'original)
                else:
                    lines[line_idx].append(current_rect)
            except Exception as e:
                if debug:
                    print(f"  -> Exception lors de l'ajout: {e}")
                lines.append([current_rect])

    # Trier les lignes de haut en bas (par y du coin supérieur droit)
    # Extraire y si RectangleWithLine, sinon utiliser l'index [1]
    lines.sort(key=lambda line: line[0].y if isinstance(line[0], RectangleWithLine) else line[0][1])  # y du coin supérieur droit du rectangle le plus à droite

    if debug:
        print(f"\n=== RÉSULTAT FINAL DE L'ORDONNANCEMENT ===")
        print(f"Nombre de lignes formées: {len(lines)}")
        for line_idx, line in enumerate(lines):
            first_rect = line[0]
            last_rect = line[-1]

            # Extraire les coordonnées
            if isinstance(first_rect, RectangleWithLine):
                top_right_x = first_rect.x + first_rect.w
                first_y = first_rect.y
                last_x = last_rect.x
            else:
                top_right_x = first_rect[0] + first_rect[2]
                first_y = first_rect[1]
                last_x = last_rect[0]

            print(f"Ligne {line_idx}: {len(line)} rectangles")
            print(f"  - Commence à x={top_right_x} (droite), y={first_y}")
            print(f"  - Finit à x={last_x} (gauche)")

            # Afficher quelques détails
            # for rect_idx, rect in enumerate(line[:3]):  # Afficher les 3 premiers de chaque ligne
            #     if isinstance(rect, RectangleWithLine):
            #         print(f"    Rect {rect_idx}: x={rect.x}, y={rect.y}")
            #     else:
            #         print(f"    Rect {rect_idx}: x={rect[0]}, y={rect[1]}")

    # Aplatir la liste en créant des RectangleWithLine avec le numéro de ligne
    # Les rectangles dans chaque ligne sont déjà de droite à gauche
    flat_list = []
    text_position = 0
    for line_idx, line in enumerate(lines):
        for rect in line:
            # Créer un RectangleWithLine avec le numéro de ligne
            # Conserver detected_letter si déjà présent
            # Initialiser text_position avec l'ordre séquentiel
            if isinstance(rect, RectangleWithLine):
                # Conserver la couleur si elle existe, sinon utiliser la valeur par défaut
                rect_with_line = RectangleWithLine(rect.x, rect.y, rect.w, rect.h, line_idx, rect.detected_letter, text_position, rect.color)
            else:
                rect_with_line = RectangleWithLine(rect[0], rect[1], rect[2], rect[3], line_idx, None, text_position)
            flat_list.append(rect_with_line)
            text_position += 1

    return flat_list, lines
