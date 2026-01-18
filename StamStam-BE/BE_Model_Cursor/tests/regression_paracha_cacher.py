"""
Test de régression pour les images dans paracha_cacher/.
Ce test vérifie que toutes les images dans paracha_cacher/ produisent un succès à 100%.
Pas de fenêtres imshow, uniquement les logs et un résultat ✓ ou ✗ pour chaque fichier.

Ce script utilise les fonctions de visualize_detect_letters.py pour éviter la duplication de code.
"""
import os
import sys
import glob

# Ajouter le chemin vers le backend pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# Importer la fonction de traitement depuis visualize_detect_letters
from visualize_detect_letters import process_single_image


def single_image_test(image_path):
    """
    Teste une seule image et retourne True si succès à 100%, False sinon.
    Utilise process_single_image de visualize_detect_letters.py.
    
    Args:
        image_path: Chemin vers l'image à tester
        
    Returns:
        tuple: (success: bool, paracha_name: str, num_differences: int)
    """
    try:
        # Utiliser la fonction partagée de visualize_detect_letters
        # show_contours=False: pas d'imshow pour les contours
        # debug=True: activer les logs détaillés
        # save_result=False: ne pas sauvegarder l'image
        result = process_single_image(
            image_path,
            show_contours=False,
            debug=True,
            save_result=False
        )
        
        if result is None:
            print(f"  ✗ ERREUR: Impossible de traiter l'image : {image_path}")
            return False, "ERREUR", -1
        
        img_base64, paracha_name, detected_text, differences_info, result_image = result
        
        # Vérifier si c'est un succès (pas de différences)
        # differences_info peut être None ou une liste vide []
        if differences_info is None:
            num_differences = 0
            success = False  # None signifie une erreur
        else:
            num_differences = len(differences_info)
            success = num_differences == 0  # Succès si pas de différences
        
        return success, paracha_name, num_differences
        
    except Exception as e:
        print(f"  ✗ ERREUR: Exception lors du traitement : {e}")
        import traceback
        traceback.print_exc()
        return False, "ERREUR", -1


def main():
    """
    Fonction principale qui teste toutes les images dans paracha_cacher/.
    """
    # Chemin vers le dossier paracha_cacher
    paracha_cacher_dir = os.path.join(current_dir, 'paracha_cacher')
    
    if not os.path.exists(paracha_cacher_dir):
        print(f"Erreur: Dossier paracha_cacher non trouvé : {paracha_cacher_dir}")
        return
    
    # Trouver toutes les images dans paracha_cacher
    # Utiliser un set pour éviter les doublons
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    image_files_set = set()
    for ext in image_extensions:
        found_files = glob.glob(os.path.join(paracha_cacher_dir, ext))
        image_files_set.update(found_files)
    
    # Convertir en liste et trier par nom de fichier
    image_files = sorted(list(image_files_set))
    
    if not image_files:
        print(f"Aucune image trouvée dans : {paracha_cacher_dir}")
        return
    
    print("="*80)
    print("TEST DE RÉGRESSION - PARACHA CACHER")
    print("="*80)
    print(f"Nombre d'images à tester : {len(image_files)}")
    print()
    
    # Résultats
    results = []
    success_count = 0
    total_count = len(image_files)
    
    # Tester chaque image
    for image_path in image_files:
        filename = os.path.basename(image_path)
        print(f"Test: {filename}", end=" ... ")
        
        success, paracha_name, num_differences = single_image_test(image_path)
        
        if success:
            print(f"✓ SUCCÈS (paracha: {paracha_name})")
            success_count += 1
        else:
            if num_differences >= 0:
                print(f"✗ ÉCHEC (paracha: {paracha_name}, différences: {num_differences})")
            else:
                print(f"✗ ERREUR")
        
        results.append({
            'filename': filename,
            'success': success,
            'paracha_name': paracha_name,
            'num_differences': num_differences
        })
    
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
        for r in failures:
            print(f"  - {r['filename']}: paracha={r['paracha_name']}, différences={r['num_differences']}")
    else:
        print("Tous les tests sont passés avec succès ! ✓")
    
    print()


if __name__ == '__main__':
    main()

