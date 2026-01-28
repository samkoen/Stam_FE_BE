"""
Classe pour représenter un rectangle avec son numéro de ligne.
Permet une vérification simple et fiable si deux rectangles sont sur la même ligne.
"""
from typing import Tuple, Optional


class RectangleWithLine:
    """
    Représente un rectangle avec son numéro de ligne, la lettre détectée, sa position dans le texte et sa couleur.
    
    Attributes:
        x: Coordonnée x du coin supérieur gauche
        y: Coordonnée y du coin supérieur gauche
        w: Largeur du rectangle
        h: Hauteur du rectangle
        line_number: Numéro de ligne (0-indexed)
        detected_letter: Lettre hébraïque détectée dans ce rectangle (None si pas encore détectée ou noise)
        text_position: Position du rectangle dans le texte (0-indexed, ordre de lecture hébreu)
        color: Couleur BGR du rectangle pour l'affichage (défaut: (0, 255, 0) = vert = correct)
    """
    
    def __init__(self, x: int, y: int, w: int, h: int, line_number: int, detected_letter: Optional[str] = None, text_position: Optional[int] = None, color: Optional[Tuple[int, int, int]] = None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.line_number = line_number
        self.detected_letter = detected_letter
        self.text_position = text_position
        # Couleur par défaut : vert (correct)
        self.color = color if color is not None else (0, 255, 0)
    
    def copy(self) -> 'RectangleWithLine':
        """
        Crée une copie de l'instance.
        
        Returns:
            Une nouvelle instance RectangleWithLine avec les mêmes valeurs.
        """
        return RectangleWithLine(
            self.x, self.y, self.w, self.h,
            self.line_number,
            self.detected_letter,
            self.text_position,
            self.color
        )
    
    def __iter__(self):
        """
        Permet de déballer le rectangle comme un tuple (x, y, w, h) pour compatibilité.
        Exemple: x, y, w, h = rect_with_line
        """
        return iter((self.x, self.y, self.w, self.h))
    
    def __getitem__(self, index: int):
        """
        Permet d'accéder aux coordonnées par index pour compatibilité.
        Exemple: rect[0] pour x, rect[1] pour y, etc.
        """
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.w
        elif index == 3:
            return self.h
        else:
            raise IndexError(f"Index {index} out of range for RectangleWithLine")
    
    def __len__(self):
        """Retourne 4 pour compatibilité avec les tuples (x, y, w, h)."""
        return 4
    
    def __repr__(self):
        letter_str = f"'{self.detected_letter}'" if self.detected_letter else "None"
        pos_str = str(self.text_position) if self.text_position is not None else "None"
        color_str = str(self.color)
        return f"RectangleWithLine(x={self.x}, y={self.y}, w={self.w}, h={self.h}, line_number={self.line_number}, detected_letter={letter_str}, text_position={pos_str}, color={color_str})"
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Retourne le rectangle sous forme de tuple (x, y, w, h)."""
        return (self.x, self.y, self.w, self.h)
    
    def is_same_line(self, other: 'RectangleWithLine') -> bool:
        """
        Vérifie si ce rectangle est sur la même ligne qu'un autre rectangle.
        
        Args:
            other: Autre RectangleWithLine à comparer
            
        Returns:
            bool: True si les rectangles sont sur la même ligne
        """
        return self.line_number == other.line_number

