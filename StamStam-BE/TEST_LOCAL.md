# Guide de test local

Ce guide explique comment tester l'application localement avant le déploiement sur un serveur.

## 📋 Prérequis

1. Python 3.8+ installé
2. Dépendances installées : `pip install -r requirements.txt`
3. Fichier `.env` créé dans `StamStam-BE/` (copié depuis `ENV_EXAMPLE.txt`)

## 🧪 Test 1 : Vérifier la configuration

### Vérifier que config.py fonctionne

```bash
cd StamStam-BE
python config.py
```

Cela affiche la configuration actuelle et vérifie les chemins.

**Sortie attendue :**
```
============================================================
Configuration StamStam
============================================================
Environnement: dev (Développement)
DEBUG: False
MODEL_PATH: C:\...\StamStam-BE\ocr\model\output\Nadam_beta_1_256_30.hdf5
OVERFLOW_DIR: C:\...\StamStam-BE\overflow
...
```

## 🚀 Test 2 : Démarrer l'API en mode développement

### Option A : Uvicorn (recommandé pour le développement)

```bash
cd StamStam-BE
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Avantages :**
- Rechargement automatique lors des modifications
- Messages d'erreur détaillés
- Parfait pour le développement

### Option B : Script de production (simuler la production)

```bash
cd StamStam-BE
python start_production.py
```

**Avantages :**
- Utilise Gunicorn (comme en production)
- Permet de tester la configuration production
- Vérifie automatiquement les prérequis

## ✅ Test 3 : Vérifier que l'API fonctionne

### Health Check

Ouvrez un nouveau terminal et testez :

```bash
# Windows PowerShell
curl http://localhost:8000/health

# Ou avec Invoke-WebRequest
Invoke-WebRequest -Uri http://localhost:8000/health

# Linux/Mac
curl http://localhost:8000/health
```

**Réponse attendue :**
```json
{
  "status": "healthy",
  "model_path_exists": true,
  "overflow_dir_exists": true,
  "environment": "dev"
}
```

### Test endpoint principal

```bash
curl http://localhost:8000/
```

**Réponse attendue :**
```json
{
  "message": "API StamStam - Backend FastAPI",
  "version": "1.0"
}
```

### Documentation Swagger (interactive)

Ouvrez dans votre navigateur :
- http://localhost:8000/docs

Cela affiche la documentation interactive de l'API où vous pouvez tester les endpoints.

### Documentation ReDoc

Ouvrez dans votre navigateur :
- http://localhost:8000/redoc

Documentation alternative de l'API.

## 🧪 Test 4 : Tester l'endpoint de détection de lettres

### Avec curl (PowerShell)

```powershell
# Préparer un fichier image pour le test
$filePath = "C:\chemin\vers\votre\image.jpg"
$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileBase64 = [System.Convert]::ToBase64String($fileBytes)

# Créer le body de la requête multipart/form-data
$boundary = [System.Guid]::NewGuid().ToString()
$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"image.jpg`"",
    "Content-Type: image/jpeg",
    "",
    [System.Text.Encoding]::ASCII.GetString($fileBytes),
    "--$boundary--"
)
$body = $bodyLines -join "`r`n"
$bodyBytes = [System.Text.Encoding]::ASCII.GetBytes($body)

# Envoyer la requête
Invoke-WebRequest -Uri http://localhost:8000/api/detect-letters -Method POST -Body $bodyBytes -ContentType "multipart/form-data; boundary=$boundary"
```

### Avec Python (plus simple)

Créez un fichier `test_api.py` dans `StamStam-BE/` :

```python
import requests

# URL de l'API
url = "http://localhost:8000/api/detect-letters"

# Chemin vers une image de test
image_path = "images/test.png"  # Modifiez selon votre chemin

# Envoyer la requête
with open(image_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Exécutez :
```bash
python test_api.py
```

### Avec le navigateur (Swagger UI)

1. Ouvrez http://localhost:8000/docs
2. Cliquez sur `POST /api/detect-letters`
3. Cliquez sur "Try it out"
4. Cliquez sur "Choose File" et sélectionnez une image
5. Cliquez sur "Execute"

## 🔍 Test 5 : Vérifier les logs

### En mode développement

Les logs sont affichés dans la console où vous avez lancé l'API.

Si `STAMSTAM_DEBUG=true` dans `.env`, vous verrez des logs détaillés.

### Vérifier le fichier de log (si configuré)

Si vous avez configuré `STAMSTAM_LOG_FILE=logs/stamstam.log` :

```bash
# Windows PowerShell
Get-Content logs/stamstam.log -Tail 50

# Linux/Mac
tail -f logs/stamstam.log
```

## ⚠️ Dépannage

### Erreur "Module not found"

```bash
# Vérifier que vous êtes dans le bon répertoire
cd StamStam-BE

# Réinstaller les dépendances
pip install -r requirements.txt
```

### Erreur "Le fichier de modèle n'existe pas"

Vérifier le chemin dans `.env` :

```bash
# Vérifier que le modèle existe
ls ocr/model/output/Nadam_beta_1_256_30.hdf5

# Ou sur Windows
dir ocr\model\output\Nadam_beta_1_256_30.hdf5
```

Si le chemin est incorrect, modifiez `STAMSTAM_MODEL_PATH` dans `.env`.

### Erreur "Le dossier overflow n'existe pas"

Vérifier :

```bash
# Vérifier que le dossier existe
ls overflow/

# Ou sur Windows
dir overflow\
```

Si le dossier n'existe pas ou le chemin est incorrect, modifiez `STAMSTAM_OVERFLOW_DIR` dans `.env`.

### L'API ne démarre pas

1. Vérifier que le port 8000 n'est pas déjà utilisé :
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

2. Changer le port dans `.env` :
   ```
   STAMSTAM_PORT=8001
   ```

### Erreur CORS

Si vous testez depuis le frontend sur un autre port, ajoutez l'origine dans `.env` :

```
STAMSTAM_CORS_ORIGINS=http://localhost:3000
```

Ou en développement, gardez `*` :
```
STAMSTAM_CORS_ORIGINS=*
```

## ✅ Checklist de test local

- [ ] Configuration vérifiée (`python config.py`)
- [ ] API démarre sans erreur
- [ ] Health check fonctionne (`/health` retourne `healthy`)
- [ ] Endpoint principal fonctionne (`/` retourne un message)
- [ ] Documentation Swagger accessible (`/docs`)
- [ ] Test upload d'image réussi (`/api/detect-letters`)
- [ ] Logs fonctionnent (visibles dans console ou fichier)
- [ ] Pas d'erreurs dans les logs

## 🎯 Test complet (recommandé)

1. **Démarrer l'API** :
   ```bash
   cd StamStam-BE
   python -m uvicorn app:app --reload
   ```

2. **Tester dans le navigateur** :
   - Ouvrez http://localhost:8000/docs
   - Testez les endpoints interactivement

3. **Tester avec le frontend** :
   - Démarrer le frontend (si disponible)
   - Configurer `API_URL` dans `StamStam-FE/js/config.js` vers `http://localhost:8000/api/detect-letters`
   - Tester l'upload d'image depuis l'interface

4. **Tester avec le frontend** :
   - Démarrer le frontend : `cd ../StamStam-FE && npm run dev`
   - Ouvrir http://localhost:3000
   - Tester l'upload d'image depuis l'interface

5. **Vérifier les logs** :
   - Regarder la console de l'API
   - Vérifier les messages de log

---

*Pour tester avec le frontend, voir aussi : `TEST_FRONTEND_BACKEND.md`*

*Si tous les tests passent, l'application est prête pour le déploiement sur un serveur !*

