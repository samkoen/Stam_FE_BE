# lenet_stam_predict_fast.py
import numpy as np
# On évite d'importer tout TensorFlow pour gagner du temps au démarrage
from .lenet import LeNet
from ocr.model import image_to_np2

# Variable globale pour maintenir le modèle "chaud" en mémoire RAM
GLOBAL_MODEL = None


def load_model_once(weight_file):
    """
    Charge l'architecture LeNet et les poids HDF5 une seule fois.
    Si le modèle est déjà en mémoire, il est renvoyé instantanément.
    """
    global GLOBAL_MODEL

    if GLOBAL_MODEL is None:
        print(f"[INFO] Initialisation du modèle avec les poids : {weight_file}")
        # Reconstruction de l'architecture définie dans lenet.py
        model = LeNet.build(
            numChannels=1,
            imgRows=image_to_np2.WIDTH,
            imgCols=image_to_np2.HEIGHT,
            numClasses=30,
            weightsPath=weight_file
        )

        # Compilation minimale nécessaire pour activer les fonctions de prédiction
        model.compile(
            loss="categorical_crossentropy",
            optimizer="adam",
            metrics=["accuracy"]
        )
        GLOBAL_MODEL = model
        print("[INFO] Modèle Stam chargé avec succès et prêt pour la prédiction.")

    return GLOBAL_MODEL


def predict(weight_file=None, testData=None):
    """
    Fonction de prédiction optimisée pour la vitesse.
    """
    # Sécurité si aucune lettre n'est détectée
    if testData is None or len(testData) == 0:
        return []

    # 1. Récupération ou chargement du modèle (Singleton)
    model = load_model_once(weight_file)

    # 2. Prétraitement des données (Batch Preprocessing)
    # Redimensionnement vers le format attendu par LeNet (N, 28, 28, 1)
    testData = testData.reshape((testData.shape[0], image_to_np2.WIDTH, image_to_np2.HEIGHT, 1))

    # Normalisation des pixels (0-255 vers 0-1) pour la précision de l'IA
    testData = testData.astype("float32") / 255.0

    # 3. Prédiction groupée (Inférence)
    # On traite toutes les lettres du bloc d'image d'un seul coup
    # verbose=0 supprime les barres de progression inutiles dans la console
    probs = model.predict(testData, batch_size=32, verbose=0)

    # 4. Conversion des probabilités en codes de lettres (0 à 29)
    # argmax récupère l'index de la lettre la plus probable pour chaque image
    predictions = probs.argmax(axis=1)

    return predictions.tolist()


if __name__ == "__main__":
    # Ce bloc ne s'exécute que si vous lancez le fichier directement pour test
    print("Module de prédiction rapide prêt. En attente d'appels de letter_separation.py.")