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

app = FastAPI()

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEIGHT_FILE = 'ocr/model/output/Nadam_beta_1_256_30.hdf5'

def check_image_api(img_src):
    """Version adaptée de check_image pour l'API, retourne l'image avec les rectangles et le nom de la paracha"""
    if img_src is None:
        raise HTTPException(status_code=400, detail="Erreur: image non lue correctement")
    
    img_src = resize(img_src)
    imgTraining = img_src.copy()
    
    npaContours = get_contour(imgTraining, gshow=False, name=None)
    letters = image_to_letters(npaContours, img_src, WEIGHT_FILE)
    
    if len(letters) == 0:
        raise HTTPException(status_code=400, detail="Aucune lettre détectée dans l'image")
    
    letters, lines = sort_contour(letters, img_src)
    
    fix_issues_box(letters, img_src, WEIGHT_FILE)
    
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
        # Lire le fichier uploadé
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Impossible de décoder l'image")
        
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
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@app.post("/api/detect-letters")
async def detect_letters_endpoint(file: UploadFile = File(...)):
    """Endpoint pour détecter les lettres dans une image, les entourer de carrés verts et détecter la paracha"""
    try:
        # Lire le fichier uploadé
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Impossible de décoder l'image")
        
        # Détecter les lettres et la paracha
        img_base64, paracha_name, detected_text, differences = detect_letters(img)
        
        # Convertir bytes en string
        img_base64_str = img_base64.decode('utf-8')
        
        return JSONResponse({
            "success": True,
            "image": img_base64_str,
            "paracha": paracha_name,
            "text": detected_text,
            "differences": differences
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la détection: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API StamStam - Backend FastAPI"}
