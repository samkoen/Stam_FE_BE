"""
Module pour ordonner les rectangles de droite à gauche et de haut en bas
(ordre de lecture hébraïque)
"""
import math


def follow_rect(rect1, rect2, width_mean):
    """
    Vérifie si rect2 suit rect1 sur la même ligne (pour l'ordre hébreu de droite à gauche).

    Args:
        rect1: Tuple (x, y, w, h) du premier rectangle
        rect2: Tuple (x, y, w, h) du deuxième rectangle
        width_mean: Largeur moyenne des rectangles

    Returns:
        float: Hauteur de chevauchement si les rectangles sont sur la même ligne, None sinon
    """
    s = max(rect1[1], rect2[1])
    h = min(rect1[1] + rect1[3], rect2[1] + rect2[3]) - s

    # Si il y a un chevauchement vertical et les rectangles sont proches horizontalement
    if h > 1 and (rect2[0] - (rect1[0] + rect1[2])) < width_mean * 8:
        return h
    return None


def is_rect_included(rect_a, rect_b):
    """
    Vérifie si rect_b est entièrement inclus dans rect_a.

    Args:
        rect_a: Tuple (x, y, w, h) du rectangle englobant
        rect_b: Tuple (x, y, w, h) du rectangle à vérifier

    Returns:
        bool: True si rect_b est inclus dans rect_a
    """
    return (rect_a[0] <= rect_b[0] and rect_b[0] + rect_b[2] <= rect_a[0] + rect_a[2] and
            rect_a[1] <= rect_b[1] and rect_b[1] + rect_b[3] <= rect_a[1] + rect_a[3])


def sort_rectangles_by_lines(rects):
    """
    Ordonne les rectangles en lignes (de droite à gauche dans chaque ligne, 
    puis de haut en bas pour les lignes).

    Inspiré de sort_contour dans letter_separation.py mais simplifié.

    Args:
        rects: Liste de tuples (x, y, w, h) représentant les rectangles

    Returns:
        list: Liste ordonnée des rectangles (de droite à gauche, haut en bas)
    """
    if not rects:
        return []

    # Calculer la largeur moyenne
    width_mean = sum(r[2] for r in rects) / len(rects) if rects else 50

    # Trier par position x décroissante (de droite à gauche)
    sorted_rects = sorted(rects, key=lambda r: r[0] + r[2], reverse=True)

    # Grouper en lignes
    lines = [[sorted_rects[0]]]  # Première ligne avec le premier rectangle

    for i in range(1, len(sorted_rects)):
        current_rect = sorted_rects[i]
        follow_candidates = []
        last_idx = -1

        # Chercher dans les lignes existantes (en regardant les derniers rectangles)
        while len(follow_candidates) == 0 and last_idx > -3:
            line_idx = 0
            for current_line in lines:
                if len(current_line) < abs(last_idx):
                    line_idx += 1
                    continue

                last_rect_in_line = current_line[last_idx]
                h_overlap = follow_rect(current_rect, last_rect_in_line, width_mean)

                if h_overlap:
                    # Vérifier que current n'est pas inclus dans un rectangle existant
                    is_included_flag = False
                    for existing_rect in current_line:
                        if is_rect_included(existing_rect, current_rect):
                            is_included_flag = True
                            break

                    if not is_included_flag:
                        follow_candidates.append((current_rect, h_overlap, line_idx, last_rect_in_line))

                line_idx += 1

            last_idx -= 1

        if len(follow_candidates) == 0:
            # Nouvelle ligne
            lines.append([current_rect])
        else:
            # Trouver le meilleur candidat (celui avec le plus de chevauchement)
            best_match = max(follow_candidates, key=lambda f: f[1])
            line_idx = best_match[2]
            try:
                lines[line_idx].append(current_rect)
            except Exception:
                # En cas d'erreur, créer une nouvelle ligne
                lines.append([current_rect])

    # Trier les lignes de haut en bas (par y croissant du premier rectangle de chaque ligne)
    lines.sort(key=lambda line: line[0][1])

    # Aplatir la liste (les rectangles dans chaque ligne sont déjà de droite à gauche)
    flat_list = [rect for line in lines for rect in line]

    return flat_list

