"""
Test de régression pour les images de test.
Ce test vérifie que les images produisent les résultats attendus en termes de :
- Nombre de lettres manquantes (missing)
- Nombre de substitutions (wrong)
- Nombre de lettres en trop (extra)
- Nombre d'espaces manquants (missing_spaces)

Les fichiers à tester et leurs résultats attendus sont hardcodés dans ce script.
"""
import os
import sys

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)
# Ajouter aussi le dossier tests pour les imports locaux
sys.path.insert(0, current_dir)

# Importer la fonction de traitement depuis visualize_detect_letters
from visualize_detect_letters import process_single_image


# Configuration des tests : fichiers et résultats attendus
TEST_CONFIG = [
    {
        'filename': '001.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,  # 'wrong' dans differences_info
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': 'chema_2mots_colles.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 1
        }
    },
    {
        'filename': '002.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
    {
        'filename': '003.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
    {
        'filename': '004.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': '005.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,  # 'wrong' dans differences_info
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': '006.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,  # 'wrong' dans differences_info
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': '007.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 1, # ds la marge basse du parchemin
            'missing_spaces': 0
        }
    },
{
        'filename': '009.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 2, # ds les marges
            'missing_spaces': 0
        }
    },
    {
        'filename': 'chema_lettre_manquante_finedeligne.jpg',
        'expected': {
            'missing': 2,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': 'chema_sans_youd.jpg',
        'expected': {
            'missing': 1,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': 'chema_manque_un_mot.jpg',
        'expected': {
            'missing': 3,
            'substitution': 0,
            'extra': 0,
            'missing_spaces': 0
        }
    },
{
        'filename': 'chema_manque_2 lignes.jpg',
        'expected': {
            'missing': 3,
            'substitution': 1,
            'extra': 0,
            'missing_spaces': 0
        }
    },
    {
        'filename': 'vehaya_avec_un_mot_en_plus.jpg',
        'expected': {
            'missing': 0,
            'substitution': 0,
            'extra': 6,
            'missing_spaces': 0
        }
    },{
        'filename': 'mezuza_mot_en_plus.jpg',
        'expected': {
            'missing': 0,
            'substitution': 1, #a ameliore
            'extra': 7,
            'missing_spaces': 0
        }
    },
    # Ajouter d'autres fichiers ici avec leurs résultats attendus

]


def count_differences(differences_info):
    """
    Compte les différents types de différences dans differences_info,
    en séparant les erreurs d'espaces des erreurs de lettres.
    
    Args:
        differences_info: Liste de dictionnaires avec les différences
        
    Returns:
        dict: {'missing': int, 'substitution': int, 'extra': int, 'missing_spaces': int}
    """
    if differences_info is None:
        return {'missing': 0, 'substitution': 0, 'extra': 0, 'missing_spaces': 0}
    
    counts = {'missing': 0, 'substitution': 0, 'extra': 0, 'missing_spaces': 0}
    
    for diff in differences_info:
        diff_type = diff.get('type', '')
        diff_text = diff.get('text', '')
        
        # Détecter si c'est une erreur d'espace
        is_space_error = (diff_text == ' ' or (diff_text and diff_text.strip() == ''))
        
        if diff_type == 'missing':
            if is_space_error:
                counts['missing_spaces'] += 1
            else:
                counts['missing'] += 1
        elif diff_type == 'wrong':
            counts['substitution'] += 1
        elif diff_type == 'extra':
            # Les espaces en trop ne sont pas comptés dans missing_spaces, seulement les manquants
            if not is_space_error:
                counts['extra'] += 1
    
    return counts


def single_image_test(image_path, expected):
    """
    Teste une seule image et compare avec les résultats attendus.
    
    Args:
        image_path: Chemin vers l'image à tester
        expected: Dictionnaire avec les résultats attendus {'missing': int, 'substitution': int, 'extra': int}
        
    Returns:
        dict: {
            'success': bool,
            'filename': str,
            'paracha_name': str,
            'expected': dict,
            'actual': dict,
            'match': dict  # {'missing': bool, 'substitution': bool, 'extra': bool}
        }
    """
    filename = os.path.basename(image_path)
    
    try:
        # Utiliser la fonction partagée de visualize_detect_letters
        # show_contours=False: pas d'imshow pour les contours
        # debug=False: pas de logs détaillés pour le test
        # save_result=False: ne pas sauvegarder l'image
        result = process_single_image(
            image_path,
            show_contours=False,
            debug=False,
            save_result=False
        )
        
        if result is None:
            return {
                'success': False,
                'filename': filename,
                'paracha_name': 'ERREUR',
                'expected': expected,
                'actual': None,
                'match': None,
                'error': 'Impossible de traiter l\'image'
            }
        
        img_base64, paracha_name, detected_text, differences_info, summary, result_image = result
        
        # Compter les différences
        actual = count_differences(differences_info)
        
        # S'assurer que missing_spaces est défini dans expected (valeur par défaut: 0)
        expected_missing_spaces = expected.get('missing_spaces', 0)
        
        # Comparer avec les résultats attendus - missing_spaces DOIT correspondre exactement
        match = {
            'missing': actual['missing'] == expected['missing'],
            'substitution': actual['substitution'] == expected['substitution'],
            'extra': actual['extra'] == expected['extra'],
            'missing_spaces': actual['missing_spaces'] == expected_missing_spaces
        }
        
        # Succès si TOUS les compteurs correspondent (y compris missing_spaces)
        # Si missing_spaces ne correspond pas, le test DOIT échouer
        success = all(match.values())
        
        # Vérification explicite : si missing_spaces ne correspond pas, forcer l'échec
        if actual['missing_spaces'] != expected_missing_spaces:
            success = False
        
        return {
            'success': success,
            'filename': filename,
            'paracha_name': paracha_name,
            'expected': expected,
            'actual': actual,
            'match': match
        }
        
    except Exception as e:
        return {
            'success': False,
            'filename': filename,
            'paracha_name': 'ERREUR',
            'expected': expected,
            'actual': None,
            'match': None,
            'error': str(e)
        }


def main():
    """
    Fonction principale qui teste toutes les images configurées.
    """
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Chemin vers le dossier de test
    test_images_dir = os.path.join(current_dir, 'regression_test_images')
    
    if not os.path.exists(test_images_dir):
        print(f"Erreur: Dossier regression_test_images non trouvé : {test_images_dir}")
        return
    
    print("="*80)
    print("TEST DE RÉGRESSION - IMAGES DE TEST")
    print("="*80)
    print(f"Nombre d'images à tester : {len(TEST_CONFIG)}")
    print()
    
    # Résultats
    results = []
    success_count = 0
    total_count = len(TEST_CONFIG)
    
    # Tester chaque image
    for test_config in TEST_CONFIG:
        filename = test_config['filename']
        expected = test_config['expected']
        image_path = os.path.join(test_images_dir, filename)
        
        if not os.path.exists(image_path):
            print(f"✗ {filename}: FICHIER NON TROUVÉ")
            results.append({
                'success': False,
                'filename': filename,
                'paracha_name': 'N/A',
                'expected': expected,
                'actual': None,
                'match': None,
                'error': 'Fichier non trouvé'
            })
            continue
        
        print(f"Test: {filename} ... ", end="", flush=True)
        
        result = single_image_test(image_path, expected)
        results.append(result)
        
        if result['success']:
            print("✓ SUCCÈS")
            success_count += 1
        else:
            print("✗ ÉCHEC")
            if 'error' in result:
                print(f"  Erreur: {result['error']}")
            else:
                print(f"  Paracha: {result['paracha_name']}")
                expected_missing_spaces = expected.get('missing_spaces', 0)
                print(f"  Attendu: missing={expected['missing']}, substitution={expected['substitution']}, extra={expected['extra']}, missing_spaces={expected_missing_spaces}")
                print(f"  Obtenu: missing={result['actual']['missing']}, substitution={result['actual']['substitution']}, extra={result['actual']['extra']}, missing_spaces={result['actual']['missing_spaces']}")
                if not result['match']['missing']:
                    print(f"    ✗ Missing: attendu {expected['missing']}, obtenu {result['actual']['missing']}")
                if not result['match']['substitution']:
                    print(f"    ✗ Substitution: attendu {expected['substitution']}, obtenu {result['actual']['substitution']}")
                if not result['match']['extra']:
                    print(f"    ✗ Extra: attendu {expected['extra']}, obtenu {result['actual']['extra']}")
                if not result['match'].get('missing_spaces', True):
                    print(f"    ✗ MISSING SPACES: attendu {expected_missing_spaces}, obtenu {result['actual']['missing_spaces']} - LE TEST ÉCHOUE CAR LES ESPACES MANQUANTS NE CORRESPONDENT PAS!")
    
    # Résumé final
    print()
    print("="*80)
    print("RÉSUMÉ")
    print("="*80)
    print(f"Total : {total_count}")
    print(f"Succès : {success_count}")
    print(f"Échecs : {total_count - success_count}")
    print()
    
    # Afficher les détails des échecs
    failures = [r for r in results if not r['success']]
    if failures:
        print("Détails des échecs :")
        print("-" * 80)
        for r in failures:
            print(f"Fichier: {r['filename']}")
            if 'error' in r:
                print(f"  Erreur: {r['error']}")
            else:
                print(f"  Paracha: {r['paracha_name']}")
                expected_missing_spaces = r['expected'].get('missing_spaces', 0)
                print(f"  Attendu: missing={r['expected']['missing']}, substitution={r['expected']['substitution']}, extra={r['expected']['extra']}, missing_spaces={expected_missing_spaces}")
                if r['actual']:
                    print(f"  Obtenu: missing={r['actual']['missing']}, substitution={r['actual']['substitution']}, extra={r['actual']['extra']}, missing_spaces={r['actual']['missing_spaces']}")
                    if r['match']:
                        if not r['match']['missing']:
                            print(f"    ✗ Missing: attendu {r['expected']['missing']}, obtenu {r['actual']['missing']}")
                        if not r['match']['substitution']:
                            print(f"    ✗ Substitution: attendu {r['expected']['substitution']}, obtenu {r['actual']['substitution']}")
                        if not r['match']['extra']:
                            print(f"    ✗ Extra: attendu {r['expected']['extra']}, obtenu {r['actual']['extra']}")
                        if not r['match'].get('missing_spaces', True):
                            print(f"    ✗ MISSING SPACES: attendu {expected_missing_spaces}, obtenu {r['actual']['missing_spaces']} - LE TEST ÉCHOUE CAR LES ESPACES MANQUANTS NE CORRESPONDENT PAS!")
            print()
    else:
        print("Tous les tests sont passés avec succès ! ✓")
    
    print()


if __name__ == '__main__':
    main()
