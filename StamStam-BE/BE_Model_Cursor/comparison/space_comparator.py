"""
Module de comparaison et correction des espaces entre le texte détecté et le texte de référence.
Utilise une approche hybride : géométrie (gaps entre rectangles) + référence (positions attendues).
"""
import diff_match_patch as dmp_module
from BE_Model_Cursor.utils.logger import get_logger
from BE_Model_Cursor.corrections.width_refinement_correction import WidthRefinementCorrection


class SpaceComparator:
    """
    Classe pour comparer et corriger les espaces dans le texte détecté
    en utilisant le texte de référence comme guide.
    """
    
    def __init__(self, debug=False):
        """
        Initialise le comparateur d'espaces.
        
        Args:
            debug: Si True, active les logs détaillés
        """
        self.debug = debug
        self.logger = get_logger(__name__, debug=debug)
        self.dmp = dmp_module.diff_match_patch()
    
    def extract_space_positions(self, text):
        """
        Extrait les positions des espaces dans un texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            list: Liste des positions (indices) où se trouvent les espaces
        """
        spaces = []
        for pos, char in enumerate(text):
            if char == ' ':
                spaces.append(pos)
        return spaces
    
    def align_letters_without_spaces(self, ref_text, det_text):
        """
        Aligne les lettres (sans espaces) entre référence et détecté
        pour établir une correspondance.
        
        Args:
            ref_text: Texte de référence (avec espaces)
            det_text: Texte détecté (avec ou sans espaces)
            
        Returns:
            dict: Mapping {position_dans_ref_chars_only: position_dans_ref_text}
            dict: Mapping {position_dans_det_chars_only: position_dans_det_text}
        """
        ref_chars_only = ref_text.replace(' ', '')
        det_chars_only = det_text.replace(' ', '')
        
        # Créer les mappings position_lettre -> position_texte_original
        ref_char_to_text_map = {}
        ref_char_pos = 0
        for i, char in enumerate(ref_text):
            if char != ' ':
                ref_char_to_text_map[ref_char_pos] = i
                ref_char_pos += 1
        
        det_char_to_text_map = {}
        det_char_pos = 0
        for i, char in enumerate(det_text):
            if char != ' ':
                det_char_to_text_map[det_char_pos] = i
                det_char_pos += 1
        
        return ref_char_to_text_map, det_char_to_text_map
    
    def find_expected_spaces(self, reference_text, detected_text_without_spaces, 
                           letter_rects, avg_width):
        """
        Trouve où les espaces DEVRAIENT être dans le texte détecté
        en utilisant le texte de référence.
        
        Args:
            reference_text: Texte de référence avec espaces
            detected_text_without_spaces: Texte détecté sans espaces
            letter_rects: Liste des rectangles des lettres détectées
            avg_width: Largeur moyenne des lettres
            
        Returns:
            list: Positions (indices dans detected_text_without_spaces) où les espaces sont attendus
        """
        # Extraire les positions d'espaces dans la référence
        ref_spaces = self.extract_space_positions(reference_text)
        
        # Aligner les lettres sans espaces
        ref_chars_only = reference_text.replace(' ', '')
        det_chars_only = detected_text_without_spaces
        
        # Utiliser diff_match_patch pour aligner
        char_diff = self.dmp.diff_main(ref_chars_only, det_chars_only)
        self.dmp.diff_cleanupSemantic(char_diff)
        
        # Mapper les positions
        ref_char_to_text_map, det_char_to_text_map = self.align_letters_without_spaces(
            reference_text, detected_text_without_spaces
        )
        
        # Pour chaque espace dans la référence, trouver la position correspondante
        # dans le texte détecté
        expected_space_positions = []
        
        for ref_space_pos in ref_spaces:
            # Trouver quelle lettre précède cet espace dans reference_text
            if ref_space_pos == 0:
                # Espace au début (peu probable mais géré)
                continue
            
            # Compter les lettres non-espaces avant ref_space_pos
            letters_before = sum(1 for i in range(ref_space_pos) if reference_text[i] != ' ')
            if letters_before == 0:
                continue
            
            # Position de la lettre dans ref_chars_only (0-indexed)
            ref_char_idx = letters_before - 1
            
            # Trouver la position correspondante dans det_chars_only via l'alignement
            det_char_idx = self._map_ref_char_to_det_char(ref_char_idx, char_diff)
            
            if det_char_idx is not None and 0 <= det_char_idx < len(detected_text_without_spaces):
                # Position dans detected_text_without_spaces où l'espace devrait être
                # (après cette lettre, donc det_char_idx + 1)
                # Mais attention : on veut l'index dans la liste des lettres (0-indexed)
                # pour pouvoir l'utiliser avec letter_rects
                expected_space_positions.append(det_char_idx + 1)
            elif self.debug:
                # Log pour comprendre pourquoi le mapping a échoué
                ref_char = ref_chars_only[ref_char_idx] if ref_char_idx < len(ref_chars_only) else '?'
                self.logger.debug(
                    f"[SpaceComparator] Mapping échoué pour espace Ref[{ref_space_pos}] "
                    f"(après lettre ref_idx={ref_char_idx}, char='{ref_char}')"
                )
        
        if self.debug:
            self.logger.debug(
                f"[SpaceComparator] {len(expected_space_positions)}/{len(ref_spaces)} "
                f"espaces de référence mappés avec succès"
            )
        
        return expected_space_positions
    
    def _map_ref_char_to_det_char(self, ref_char_idx, char_diff):
        """
        Mappe une position de lettre dans ref_chars_only vers det_chars_only
        en utilisant le diff.
        
        Args:
            ref_char_idx: Index dans ref_chars_only
            char_diff: Diff entre ref_chars_only et det_chars_only
            
        Returns:
            int ou None: Index correspondant dans det_chars_only, ou None si non trouvé
        """
        ref_pos = 0
        det_pos = 0
        
        for op, text in char_diff:
            if op == 0:  # Égalité
                # Les deux textes ont les mêmes caractères
                if ref_pos <= ref_char_idx < ref_pos + len(text):
                    # La lettre recherchée est dans cette section
                    offset = ref_char_idx - ref_pos
                    return det_pos + offset
                ref_pos += len(text)
                det_pos += len(text)
            elif op == -1:  # Manquant dans détecté
                # Caractères dans la référence mais pas dans le détecté
                # Si la lettre recherchée est dans cette section manquante,
                # on ne peut pas la mapper directement
                if ref_pos <= ref_char_idx < ref_pos + len(text):
                    # La lettre est manquante dans le détecté
                    # On retourne None car on ne peut pas mapper
                    return None
                ref_pos += len(text)
            elif op == 1:  # En trop dans détecté
                # Caractères dans le détecté mais pas dans la référence
                # On avance seulement dans det_pos
                det_pos += len(text)
        
        return None
    
    def detect_spaces_from_geometry(self, letter_rects, avg_width, space_threshold_ratio=0.45):
        """
        Détecte les espaces basés uniquement sur la géométrie (gaps entre rectangles).
        
        Args:
            letter_rects: Liste des rectangles des lettres
            avg_width: Largeur moyenne des lettres
            space_threshold_ratio: Ratio du seuil (par défaut 45% de la largeur moyenne)
            
        Returns:
            list: Positions (indices) où des espaces ont été détectés géométriquement
        """
        if len(letter_rects) < 2:
            return []
        
        space_threshold = avg_width * space_threshold_ratio
        detected_spaces = []
        
        for i in range(len(letter_rects) - 1):
            current_rect = letter_rects[i]
            next_rect = letter_rects[i + 1]
            
            # Vérifier si sur la même ligne
            same_line = self._are_on_same_line(current_rect, next_rect, avg_width)
            
            if same_line:
                # Calculer le gap
                gap = self._calculate_gap(current_rect, next_rect)
                
                # Ajustement pour Lamed
                gap_adjusted = gap
                if self._is_lamed(current_rect):
                    lamed_bonus = avg_width * 0.3
                    gap_adjusted += lamed_bonus
                
                if gap_adjusted > space_threshold:
                    detected_spaces.append(i + 1)  # Espace après la lettre i
            else:
                # Changement de ligne = espace
                detected_spaces.append(i + 1)
        
        return detected_spaces
    
    def _are_on_same_line(self, rect1, rect2, avg_width):
        """Vérifie si deux rectangles sont sur la même ligne."""
        from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
        from BE_Model_Cursor.utils.contour_detector import _in_same_line
        
        if isinstance(rect1, RectangleWithLine) and isinstance(rect2, RectangleWithLine):
            return rect1.line_number == rect2.line_number
        else:
            return _in_same_line(rect1, rect2, avg_width)
    
    def _calculate_gap(self, current_rect, next_rect):
        """Calcule le gap horizontal entre deux rectangles (hébreu: droite à gauche)."""
        from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
        
        c_x = current_rect.x if isinstance(current_rect, RectangleWithLine) else current_rect[0]
        c_w = current_rect.w if isinstance(current_rect, RectangleWithLine) else current_rect[2]
        n_x = next_rect.x if isinstance(next_rect, RectangleWithLine) else next_rect[0]
        n_w = next_rect.w if isinstance(next_rect, RectangleWithLine) else next_rect[2]
        
        # Gap = distance entre fin de next et début de current
        gap = c_x - (n_x + n_w)
        return gap
    
    def _is_lamed(self, rect):
        """Vérifie si un rectangle représente un Lamed."""
        from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
        
        if isinstance(rect, RectangleWithLine) and rect.detected_letter:
            return rect.detected_letter == 'ל'
        return False
    
    def compare_and_correct_spaces(self, reference_text, detected_text_without_spaces,
                                   letter_rects, avg_width, space_threshold_ratio=0.45, image=None):
        """
        Compare les espaces détectés avec ceux attendus et corrige le texte détecté.
        
        Cette méthode utilise une approche hybride :
        1. Détecte les espaces géométriquement (gaps)
        2. Identifie les espaces attendus depuis la référence
        3. Combine les deux pour décider où placer les espaces
        
        Args:
            reference_text: Texte de référence avec espaces
            detected_text_without_spaces: Texte détecté sans espaces
            letter_rects: Liste des rectangles des lettres détectées
            avg_width: Largeur moyenne des lettres
            space_threshold_ratio: Ratio du seuil géométrique (défaut: 0.45)
            
        Returns:
            str: Texte détecté avec espaces corrigés
            dict: Statistiques de comparaison
        """
        # 1. Détection géométrique
        geometric_spaces = self.detect_spaces_from_geometry(
            letter_rects, avg_width, space_threshold_ratio
        )
        
        # 2. Espaces attendus depuis la référence
        expected_spaces = self.find_expected_spaces(
            reference_text, detected_text_without_spaces, letter_rects, avg_width
        )
        
        # 3. Combiner les deux approches
        # Stratégie améliorée :
        # - PRIORITÉ 1 : Espaces attendus dans la référence (on les place toujours)
        # - PRIORITÉ 2 : Espaces géométriques validés (gap significatif ET pas en conflit avec référence)
        # - On évite les espaces en trop en vérifiant qu'ils ne sont pas proches d'un espace attendu
        
        final_space_positions = set()
        
        # PRIORITÉ 1 : Ajouter les espaces attendus (référence)
        # MAIS vérifier qu'il y a un minimum de gap physique.
        # Si les mots sont vraiment collés (gap très faible), on ne doit pas inventer l'espace,
        # pour que cela soit signalé comme une erreur "espace manquant".
        # Augmentation du seuil à 25% pour rejeter les gaps ambigus (comme 6px vs 35px avg)
        min_gap_threshold = avg_width * 0.25  # 25% de la largeur moyenne
        
        for pos in expected_spaces:
            if 0 < pos <= len(detected_text_without_spaces):
                # Vérifier le gap géométrique
                # pos est 1-based (espace après la lettre pos), donc pos-1 est l'index dans letter_rects
                if pos <= len(letter_rects):
                    rect_idx = pos - 1
                    
                    # Vérifier s'il y a une lettre suivante
                    if rect_idx < len(letter_rects) - 1:
                        current_rect = letter_rects[rect_idx]
                        next_rect = letter_rects[rect_idx + 1]
                        
                        # Si changement de ligne, on ajoute toujours l'espace
                        if not self._are_on_same_line(current_rect, next_rect, avg_width):
                            final_space_positions.add(pos)
                        else:
                            # Même ligne : vérifier le gap
                            gap = self._calculate_gap(current_rect, next_rect)
                            
                            # Définir le seuil minimal pour accepter l'espace
                            current_min_threshold = min_gap_threshold
                            
                            # Si c'est un Lamed, on est beaucoup plus tolérant car sa "tête"
                            # s'étend vers la gauche et réduit artificiellement le gap.
                            # Si le gap est positif (ne se chevauche pas), c'est généralement bon pour un Lamed.
                            if self._is_lamed(current_rect):
                                # On accepte dès qu'il y a un micro-espace (2 pixels)
                                current_min_threshold = 2
                            
                            if gap > current_min_threshold:
                                final_space_positions.add(pos)
                            elif image is not None:
                                # TENTATIVE DE CORRECTION : Le gap est trop petit, mais la référence dit espace.
                                # Peut-être que les rectangles sont trop larges (ligne incluse) ?
                                # On essaie de raffiner les deux rectangles adjacents.
                                
                                # Import nécessaire ici si non fait globalement (mais j'ai ajouté l'import global RectangleWithLine)
                                from BE_Model_Cursor.utils.rectangle_with_line import RectangleWithLine
                                
                                # Instancier la correction
                                width_corrector = WidthRefinementCorrection(image, debug=self.debug)
                                
                                refined_current_list = width_corrector.refine_rect(current_rect)
                                refined_next_list = width_corrector.refine_rect(next_rect)
                                
                                # Si vide (ne devrait pas arriver), on garde l'original dans une liste
                                if not refined_current_list: refined_current_list = [current_rect]
                                if not refined_next_list: refined_next_list = [next_rect]
                                
                                # Pour le calcul du gap (Hébreu : Droite -> Gauche)
                                # current_rect est à droite (index i). next_rect est à gauche (index i+1).
                                # Gap = current.left - next.right
                                
                                # Pour current (à droite), on veut son bord GAUCHE (min x)
                                refined_current = min(refined_current_list, key=lambda r: r.x if hasattr(r, 'x') else r[0])
                                
                                # Pour next (à gauche), on veut son bord DROIT (max x+w)
                                refined_next = max(refined_next_list, key=lambda r: (r.x + r.w) if hasattr(r, 'x') else (r[0] + r[2]))
                                
                                # Recalculer le gap avec les rectangles raffinés
                                new_gap = self._calculate_gap(refined_current, refined_next)
                                
                                if new_gap > current_min_threshold:
                                    if self.debug:
                                        self.logger.debug(f"[SpaceComparator] Espace à pos {pos} SAUVÉ par raffinement (gap: {gap:.1f} -> {new_gap:.1f})")
                                    final_space_positions.add(pos)
                                    
                                    # Mise à jour des rectangles dans la liste originale
                                    # On ne met à jour que si on n'a pas splitté (1 seul rect retourné)
                                    # Si splitté, on ne touche pas à la structure letter_rects ici pour ne pas casser les indices
                                    if len(refined_current_list) == 1:
                                        if not isinstance(current_rect, RectangleWithLine) and not hasattr(refined_current_list[0], 'x'):
                                             letter_rects[rect_idx] = refined_current_list[0]
                                        # Si c'est un RectangleWithLine, il a peut-être été modifié en place ou remplacé
                                        # Dans le doute on remplace si c'est compatible
                                        elif isinstance(current_rect, RectangleWithLine) and isinstance(refined_current_list[0], RectangleWithLine):
                                             letter_rects[rect_idx] = refined_current_list[0]
                                             
                                    if len(refined_next_list) == 1:
                                        if not isinstance(next_rect, RectangleWithLine) and not hasattr(refined_next_list[0], 'x'):
                                             letter_rects[rect_idx + 1] = refined_next_list[0]
                                        elif isinstance(next_rect, RectangleWithLine) and isinstance(refined_next_list[0], RectangleWithLine):
                                             letter_rects[rect_idx + 1] = refined_next_list[0]
                                        
                                elif self.debug:
                                    self.logger.debug(f"[SpaceComparator] Espace à pos {pos} IGNORÉ même après raffinement (gap: {gap:.1f} -> {new_gap:.1f} <= {current_min_threshold:.1f})")
                            elif self.debug:
                                self.logger.debug(f"[SpaceComparator] Espace attendu à pos {pos} IGNORÉ car gap trop faible ({gap:.1f} <= {current_min_threshold:.1f})")
                    else:
                        # Fin de la liste des rectangles (dernier caractère), on ajoute
                        final_space_positions.add(pos)
                else:
                    # Cas limite, on ajoute par sécurité
                    final_space_positions.add(pos)
        
        # PRIORITÉ 2 : Pour les espaces détectés géométriquement mais pas dans la référence,
        # vérifier si le gap est vraiment significatif ET qu'il n'y a pas d'espace attendu proche
        for pos in geometric_spaces:
            if pos not in final_space_positions:
                # Vérifier le gap réel
                if pos > 0 and pos <= len(letter_rects):
                    idx = pos - 1
                    if idx < len(letter_rects) - 1:
                        gap = self._calculate_gap(letter_rects[idx], letter_rects[idx + 1])
                        gap_adjusted = gap
                        if self._is_lamed(letter_rects[idx]):
                            gap_adjusted += avg_width * 0.3
                        
                        # Seuil plus strict pour les espaces non référencés
                        strict_threshold = avg_width * 0.6
                        
                        # Vérifier qu'il n'y a pas d'espace attendu très proche (dans un rayon de 2 lettres)
                        # pour éviter les doublons
                        has_nearby_expected = False
                        for exp_pos in expected_spaces:
                            if abs(exp_pos - pos) <= 2:
                                has_nearby_expected = True
                                break
                        
                        # Ajouter seulement si gap significatif ET pas d'espace attendu proche
                        if gap_adjusted > strict_threshold and not has_nearby_expected:
                            final_space_positions.add(pos)
        
        # 4. Construire le texte final avec espaces
        # final_space_positions contient les indices de lettres (1-indexed: après quelle lettre)
        # On doit les convertir en positions dans le texte final
        final_text = ""
        space_positions_sorted = sorted(final_space_positions)
        space_idx = 0
        
        for i, char in enumerate(detected_text_without_spaces):
            final_text += char
            # Vérifier si on doit ajouter un espace après ce caractère
            # i+1 est l'index de la lettre suivante (1-indexed)
            if space_idx < len(space_positions_sorted):
                if i + 1 == space_positions_sorted[space_idx]:
                    final_text += ' '
                    space_idx += 1
        
        # 5. Calculer les statistiques
        ref_spaces = self.extract_space_positions(reference_text)
        final_spaces = self.extract_space_positions(final_text)
        
        # Convertir les positions d'espaces en indices de lettres (pour comparaison)
        # expected_spaces sont déjà des indices de lettres (après quelle lettre)
        # final_spaces sont des positions dans le texte final (avec espaces)
        # On doit convertir final_spaces en indices de lettres
        
        # Construire la liste des indices de lettres où il y a des espaces dans final_text
        final_space_letter_indices = []
        letter_idx = 0
        for i, char in enumerate(final_text):
            if char == ' ':
                # L'espace est après la lettre à l'index letter_idx
                final_space_letter_indices.append(letter_idx + 1)
            else:
                letter_idx += 1
        
        # Comparer
        expected_set = set(expected_spaces)
        final_set = set(final_space_letter_indices)
        
        correct = len(expected_set & final_set)
        missing = len(expected_set - final_set)
        extra = len(final_set - expected_set)
        
        stats = {
            'geometric_spaces': len(geometric_spaces),
            'expected_spaces': len(expected_spaces),
            'final_spaces': len(final_spaces),
            'correct': correct,
            'missing': missing,
            'extra': extra,
            'precision': (correct / len(ref_spaces) * 100) if len(ref_spaces) > 0 else 0
        }
        
        if self.debug:
            self.logger.debug(f"[SpaceComparator] Espaces géométriques détectés: {len(geometric_spaces)}")
            self.logger.debug(f"[SpaceComparator] Espaces attendus (référence): {len(expected_spaces)}")
            self.logger.debug(f"[SpaceComparator] Espaces finaux après combinaison: {len(final_space_positions)}")
            self.logger.debug(f"[SpaceComparator] Stats: {stats}")
            
            # Log détaillé des premiers espaces pour debug
            if len(expected_spaces) > 0:
                self.logger.debug(f"[SpaceComparator] Premiers espaces attendus: {expected_spaces[:10]}")
            if len(geometric_spaces) > 0:
                self.logger.debug(f"[SpaceComparator] Premiers espaces géométriques: {geometric_spaces[:10]}")
            if len(final_space_positions) > 0:
                sorted_final = sorted(final_space_positions)
                self.logger.debug(f"[SpaceComparator] Premiers espaces finaux: {sorted_final[:10]}")
        
        return final_text, stats

