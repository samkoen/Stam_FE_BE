"""
Module pour comparer le texte détecté avec les parachot et identifier la paracha
"""
import os
import io
import diff_match_patch as dmp_module


def read_paracha_text(file_path):
    """
    Lit un fichier texte de paracha en encodage UTF-16.
    
    Args:
        file_path: Chemin vers le fichier texte de la paracha
        
    Returns:
        list: Liste des lignes du texte (sans les retours à la ligne)
    """
    try:
        with io.open(file_path, 'r', encoding='UTF-16') as file:
            lines = [line.rstrip() for line in file]
        return lines
    except Exception as e:
        print(f"Erreur lors de la lecture de {file_path}: {e}")
        return []


def load_paracha_texts(base_path):
    """
    Charge tous les textes des parachot depuis le dossier overflow/.
    
    Args:
        base_path: Chemin de base vers le dossier contenant les fichiers texte
        
    Returns:
        dict: Dictionnaire {nom_paracha: texte_complet}
    """
    # Noms des parachot dans le même ordre que dans main.py
    paracha_files = {
        'Chema': 'chema.txt',
        'Chamoa': 'chamoa.txt',
        'Kadesh': 'kadesh.txt',
        'Kiyeviaha': 'kiyeviaha.txt',
        'Mezuza': 'mezuza.txt'
    }
    
    paracha_texts = {}
    
    for paracha_name, filename in paracha_files.items():
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            lines = read_paracha_text(file_path)
            # Joindre toutes les lignes en un seul texte
            paracha_texts[paracha_name] = ''.join(lines)
        else:
            print(f"Avertissement: fichier {file_path} introuvable")
            paracha_texts[paracha_name] = ''
    
    return paracha_texts


def compare_with_parachot(detected_text, base_path):
    """
    Compare le texte détecté avec tous les textes des parachot et retourne la meilleure correspondance.
    
    Args:
        detected_text: Texte hébreu détecté (string)
        base_path: Chemin de base vers le dossier overflow/ contenant les fichiers texte
        
    Returns:
        tuple: (diff_result, paracha_name) où diff_result est le résultat de la comparaison
               et paracha_name est le nom de la paracha détectée
    """
    print(f"\n=== DÉTECTION DE PARACHA ===")
    print(f"Texte détecté (longueur: {len(detected_text)}): {detected_text[:100]}..." if len(detected_text) > 100 else f"Texte détecté (longueur: {len(detected_text)}): {detected_text}")
    
    # Charger tous les textes des parachot
    paracha_texts = load_paracha_texts(base_path)
    
    if not paracha_texts:
        print("ERREUR: Aucun texte de paracha chargé")
        return None, "Non détectée"
    
    # Initialiser diff_match_patch
    dmp = dmp_module.diff_match_patch()
    
    # Comparer avec chaque paracha
    diff_results = {}
    print("\nComparaisons avec les parachot:")
    for paracha_name, reference_text in paracha_texts.items():
        diff = dmp.diff_main(reference_text, detected_text)
        num_diffs = len(diff)
        print(f"  - {paracha_name}: {num_diffs} différences (texte ref longueur: {len(reference_text)})")
        diff_results[paracha_name] = diff
    
    # Trouver la meilleure correspondance initiale (celle avec le moins de différences)
    best_match = min(diff_results.items(), key=lambda item: len(item[1]))
    initial_paracha_name = best_match[0]
    initial_diff_count = len(best_match[1])
    
    # Cas spécial: Si Chema ou Chamoa est détecté, vérifier aussi avec Mezuza
    # Car Mezuza = Chema + Chamoa
    if initial_paracha_name in ['Chema', 'Chamoa']:
        chema_diffs = len(diff_results.get('Chema', []))
        chamoa_diffs = len(diff_results.get('Chamoa', []))
        mezuza_diffs = len(diff_results.get('Mezuza', []))
        
        # Calculer la somme des différences de Chema + Chamoa
        chema_chamoa_sum = chema_diffs + chamoa_diffs
        
        print(f"\n⚠️  Détection de {initial_paracha_name}, vérification avec Mezuza:")
        print(f"  - Chema: {chema_diffs} différences")
        print(f"  - Chamoa: {chamoa_diffs} différences")
        print(f"  - Somme Chema + Chamoa: {chema_chamoa_sum} différences")
        print(f"  - Mezuza: {mezuza_diffs} différences")
        
        # Vérifier si la somme est "à peu près égale" à Mezuza (à 40 différences près)
        diff_threshold = 40
        diff_abs = abs(chema_chamoa_sum - mezuza_diffs)
        
        if diff_abs <= diff_threshold:
            # La somme est à peu près égale à Mezuza, choisir Mezuza
            print(f"  → Somme ≈ Mezuza (différence: {diff_abs} <= {diff_threshold}), choix: Mezuza")
            paracha_name = 'Mezuza'
            diff_result = diff_results['Mezuza']
        else:
            # Sinon, choisir entre Chema et Chamoa celui qui a le moins de différences
            if chema_diffs <= chamoa_diffs:
                print(f"  → Somme ≠ Mezuza (différence: {diff_abs} > {diff_threshold}), choix: Chema ({chema_diffs} <= {chamoa_diffs})")
                paracha_name = 'Chema'
                diff_result = diff_results['Chema']
            else:
                print(f"  → Somme ≠ Mezuza (différence: {diff_abs} > {diff_threshold}), choix: Chamoa ({chamoa_diffs} < {chema_diffs})")
                paracha_name = 'Chamoa'
                diff_result = diff_results['Chamoa']
    else:
        # Pas de cas spécial, utiliser le meilleur match initial
        paracha_name = initial_paracha_name
        diff_result = best_match[1]
    
    print(f"\n✅ Paracha détectée: {paracha_name} ({len(diff_result)} différences)")
    print("=" * 50 + "\n")
    
    return diff_result, paracha_name


def letter_codes_to_text(letter_codes):
    """
    Convertit une liste de codes de lettres en texte hébreu.
    
    Args:
        letter_codes: Liste des codes de lettres (0-29) détectées
        
    Returns:
        str: Texte hébreu correspondant
    """
    text_chars = []
    for code in letter_codes:
        if code is None or code == 27:  # 27 = zevel/noise
            continue
        if 0 <= code <= 29:
            char = chr(code + 1488)
            text_chars.append(char)
    
    return ''.join(text_chars)


def detect_paracha(letter_codes, base_path):
    """
    Détecte la paracha à partir des codes de lettres détectés.
    
    Args:
        letter_codes: Liste des codes de lettres (0-29) détectées dans l'ordre
        base_path: Chemin de base vers le dossier overflow/ contenant les fichiers texte
        
    Returns:
        tuple: (paracha_name, detected_text) où paracha_name est le nom de la paracha détectée
               et detected_text est le texte hébreu détecté
    """
    print(f"\n[detect_paracha] Nombre de codes de lettres reçus: {len(letter_codes)}")
    
    # Convertir les codes en texte hébreu
    detected_text = letter_codes_to_text(letter_codes)
    
    print(f"[detect_paracha] Texte converti (longueur: {len(detected_text)})")
    
    # Comparer avec les parachot
    _, paracha_name = compare_with_parachot(detected_text, base_path)
    
    return paracha_name, detected_text

