from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import os
import sys
from io import BytesIO
import base64

# Ajouter le répertoire courant au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from first_processing import get_contour, resize
from ocr.Letter import image_to_letters, sort_contour, fix_issues_box
from main import (
    compare_with_right_paracha, 
    print_result, 
    remove_wrong_line,
    fix_issues_box_after_comparison,
    get_image_result,
    read_source_text
)
from BE_Model_Cursor.letter_detection import detect_letters
from BE_Model_Cursor.utils.logger import get_logger
from BE_Model_Cursor.storage import ImageStorage
from fastapi import Form

app = FastAPI()

# Initialiser le logger
logger = get_logger(__name__, debug=config.DEBUG)

# Initialiser le stockage d'images
image_storage = ImageStorage(config.USER_STORAGE_DIR)

# Configuration CORS depuis config.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_uploaded_file(file: UploadFile) -> None:
    """
    Valide un fichier uploadé (taille et format).
    
    Args:
        file: Fichier uploadé
        
    Raises:
        HTTPException: Si le fichier est invalide (taille ou format)
    """
    # Vérifier le format du fichier
    if file.content_type not in config.ACCEPTED_IMAGE_FORMATS:
        allowed_types = ', '.join(config.ACCEPTED_IMAGE_FORMATS)
        raise HTTPException(
            status_code=400,
            detail=f"Format de fichier non supporté. Formats acceptés: {allowed_types}"
        )
    
    # Note: La taille sera vérifiée après la lecture, car FastAPI ne donne pas accès direct à file.size
    # On vérifiera la taille après avoir lu le contenu

def check_image_api(img_src):
    """Version adaptée de check_image pour l'API, retourne l'image avec les rectangles et le nom de la paracha"""
    if img_src is None:
        raise HTTPException(status_code=400, detail="Erreur: image non lue correctement")
    
    img_src = resize(img_src)
    imgTraining = img_src.copy()
    
    npaContours = get_contour(imgTraining, gshow=False, name=None)
    letters = image_to_letters(npaContours, img_src, config.MODEL_PATH)
    
    if len(letters) == 0:
        raise HTTPException(status_code=400, detail="Aucune lettre détectée dans l'image")
    
    letters, lines = sort_contour(letters, img_src)
    
    fix_issues_box(letters, img_src, config.MODEL_PATH)
    
    # Comparaison 1
    x, paracha_name = compare_with_right_paracha(letters)
    print_result(x, letters)
    
    # Supprimer les lignes incorrectes
    letters = remove_wrong_line(lines, letters)
    
    x, paracha_name = compare_with_right_paracha(letters)
    print_result(x, letters)
    
    # Correction après comparaison 1
    letters = fix_issues_box_after_comparison(x, letters, img_src, show=False)
    
    # Comparaison 2
    x, paracha_name = compare_with_right_paracha(letters)
    print_result(x, letters)
    
    # Correction après comparaison 2
    letters = fix_issues_box_after_comparison(x, letters, img_src, show=False)
    
    # Générer l'image avec les rectangles colorés
    img_result = get_image_result(letters, img_src)
    
    return img_result, paracha_name

@app.post("/api/process-image")
async def process_image(file: UploadFile = File(...)):
    """Endpoint pour traiter une image et retourner l'image annotée"""
    try:
        # Valider le format du fichier
        validate_uploaded_file(file)
        
        # Lire le fichier uploadé
        contents = await file.read()
        
        # Vérifier la taille du fichier après lecture
        file_size_mb = len(contents) / (1024 * 1024)
        if file_size_mb > config.MAX_UPLOAD_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux ({file_size_mb:.2f} MB). Taille maximale: {config.MAX_UPLOAD_SIZE_MB} MB"
            )
        
        # Décoder l'image
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Impossible de décoder l'image. Format d'image invalide.")
        
        # Traiter l'image
        img_base64, paracha_name = check_image_api(img)
        
        # Convertir bytes en string
        img_base64_str = img_base64.decode('utf-8')
        
        return JSONResponse({
            "success": True,
            "image": img_base64_str,
            "paracha": paracha_name
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image: {e}", exc_info=True)
        # En production, ne pas exposer les détails de l'erreur pour la sécurité
        error_detail = "Erreur lors du traitement de l'image" if config.IS_PRODUCTION else str(e)
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/detect-letters")
async def detect_letters_endpoint(
    file: UploadFile = File(...),
    email: str = Form(...)
):
    """Endpoint pour détecter les lettres dans une image, les entourer de carrés verts et détecter la paracha"""
    try:
        # Valider l'email (format basique)
        if not email or '@' not in email:
            raise HTTPException(status_code=400, detail="Email invalide")
        
        # Valider le format du fichier
        validate_uploaded_file(file)
        
        # Lire le fichier uploadé
        contents = await file.read()
        
        # Vérifier la taille du fichier après lecture
        file_size_mb = len(contents) / (1024 * 1024)
        if file_size_mb > config.MAX_UPLOAD_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux ({file_size_mb:.2f} MB). Taille maximale: {config.MAX_UPLOAD_SIZE_MB} MB"
            )
        
        # Décoder l'image
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Impossible de décoder l'image. Format d'image invalide.")
        
        # Détecter les lettres et la paracha
        # Utiliser les chemins depuis config.py
        img_base64, paracha_name, detected_text, differences, summary = detect_letters(
            img,
            weight_file=config.MODEL_PATH,
            overflow_dir=config.OVERFLOW_DIR,
            debug=config.DEBUG
        )
        
        # Décoder l'image de résultat pour la sauvegarder
        img_bytes = base64.b64decode(img_base64)
        result_nparr = np.frombuffer(img_bytes, np.uint8)
        result_img = cv2.imdecode(result_nparr, cv2.IMREAD_COLOR)
        
        # Sauvegarder les images (originale et résultat) avec le nom de la paracha
        if result_img is not None:
            image_storage.save_image_pair(
                email=email,
                original_image=img,
                result_image=result_img,
                original_filename=file.filename,
                paracha_name=paracha_name
            )
            logger.info(f"Images sauvegardées pour l'utilisateur: {email}, paracha: {paracha_name}")
        
        # Convertir bytes en string
        img_base64_str = img_base64.decode('utf-8')
        
        return JSONResponse({
            "success": True,
            "image": img_base64_str,
            "paracha": paracha_name,
            "text": detected_text,
            "differences": differences,
            "paracha_status": summary.get("paracha_status"),
            "has_errors": summary.get("has_errors"),
            "errors": summary.get("errors"),
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la détection: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API StamStam - Backend FastAPI", "version": "1.0"}

@app.get("/health")
async def health_check():
    """
    Endpoint de health check pour vérifier que l'API fonctionne.
    """
    health_status = {
        "status": "healthy",
        "model_path_exists": os.path.exists(config.MODEL_PATH),
        "overflow_dir_exists": os.path.exists(config.OVERFLOW_DIR),
        "environment": config.ENV
    }
    
    # Si le modèle ou overflow n'existent pas, marquer comme unhealthy
    if not health_status["model_path_exists"] or not health_status["overflow_dir_exists"]:
        health_status["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status
