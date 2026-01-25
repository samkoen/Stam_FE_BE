# Guide de test Frontend + Backend

Ce guide explique comment tester l'application complète avec le frontend et le backend ensemble.

## 🎯 Vue d'ensemble

Pour tester l'application complète, vous avez besoin de **2 terminaux** :

- **Terminal 1** : Backend FastAPI (port 8000)
- **Terminal 2** : Frontend Vite (port 3000)

## 📋 Prérequis

1. **Backend** : Python 3.8+ avec dépendances installées
2. **Frontend** : Node.js 16+ avec npm
3. Les deux projets doivent être prêts

## 🚀 Démarrage - Option 1 : Développement (Recommandé)

### Terminal 1 : Démarrer le Backend

```bash
cd StamStam-BE
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Vérification :** Vous devriez voir :
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Terminal 2 : Démarrer le Frontend

```bash
cd StamStam-FE
npm run dev
```

**Vérification :** Le navigateur s'ouvre automatiquement sur `http://localhost:3000`

## ✅ Vérification que tout fonctionne

### 1. Vérifier le Backend

Dans un navigateur ou avec curl :
- http://localhost:8000/health
- http://localhost:8000/docs (documentation Swagger)

### 2. Vérifier le Frontend

- http://localhost:3000 (interface de l'application)

### 3. Tester l'upload d'image

1. Ouvrez http://localhost:3000
2. Cliquez sur "Choisir une image" ou glissez-déposez une image
3. Cliquez sur "זהה אותיות" (Détecter les lettres)
4. Attendez le résultat

**Si tout fonctionne :**
- ✅ L'image est affichée avec des rectangles colorés
- ✅ Le nom de la paracha est affiché
- ✅ Les différences (si présentes) sont listées

## 🔍 Configuration actuelle

### Frontend (`StamStam-FE/js/config.js`)

```javascript
API_URL: 'http://localhost:8000/api/process-image',
API_DETECT_LETTERS: 'http://localhost:8000/api/detect-letters',
```

**Port frontend :** 3000 (Vite)
**Port backend :** 8000 (FastAPI)

### Backend (`StamStam-BE/app.py`)

```python
CORS_ORIGINS = config.CORS_ORIGINS
```

**En développement :** `["*"]` (toutes les origines autorisées)

## ⚠️ Dépannage

### Erreur CORS dans la console du navigateur

**Problème :** `Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Solution :** Vérifier que CORS est configuré correctement :

1. Vérifier `.env` dans `StamStam-BE/` :
   ```
   STAMSTAM_CORS_ORIGINS=*
   ```

2. Ou ajouter explicitement localhost:3000 :
   ```
   STAMSTAM_CORS_ORIGINS=http://localhost:3000
   ```

3. Redémarrer le backend

### Le backend ne démarre pas

```bash
# Vérifier que le port 8000 n'est pas utilisé
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

Si le port est utilisé, changer le port dans `.env` :
```
STAMSTAM_PORT=8001
```

Et mettre à jour `config.js` dans le frontend :
```javascript
API_URL: 'http://localhost:8001/api/process-image',
```

### Le frontend ne démarre pas

```bash
# Vérifier que Node.js est installé
node --version

# Installer les dépendances si nécessaire
cd StamStam-FE
npm install

# Vérifier que le port 3000 n'est pas utilisé
netstat -ano | findstr :3000
```

### Erreur "Network error" ou "שגיאת חיבור לשרת"

**Vérifier :**
1. Le backend est bien démarré (terminal 1)
2. Le backend répond sur http://localhost:8000/health
3. L'URL dans `config.js` correspond au port du backend
4. Aucun firewall ne bloque la connexion

### Les images ne s'affichent pas

**Vérifier :**
1. Le format de l'image (jpg, jpeg, png)
2. La taille de l'image (max 10 MB)
3. Les logs du backend pour voir les erreurs

## 🧪 Test complet étape par étape

### Étape 1 : Préparation

```bash
# Terminal 1 - Vérifier la configuration backend
cd StamStam-BE
python config.py

# Terminal 2 - Vérifier les dépendances frontend
cd StamStam-FE
npm install
```

### Étape 2 : Démarrer le Backend

```bash
# Terminal 1
cd StamStam-BE
python -m uvicorn app:app --reload
```

**Attendre :** `INFO: Application startup complete.`

### Étape 3 : Démarrer le Frontend

```bash
# Terminal 2
cd StamStam-FE
npm run dev
```

**Attendre :** Le navigateur s'ouvre sur `http://localhost:3000`

### Étape 4 : Tester

1. Ouvrir http://localhost:3000
2. Cliquer sur "Choisir une image"
3. Sélectionner une image (jpg/png)
4. Cliquer sur "זהה אותיות"
5. Vérifier le résultat

## 📊 Logs à surveiller

### Backend (Terminal 1)

Vous devriez voir :
```
INFO:     127.0.0.1:xxxxx - "POST /api/detect-letters HTTP/1.1" 200 OK
```

En mode debug (`STAMSTAM_DEBUG=true`), vous verrez aussi les logs détaillés du traitement.

### Frontend (Terminal 2)

Vite affiche les requêtes de rechargement et les erreurs de compilation.

### Console du navigateur (F12)

Ouvrez les outils de développement (F12) pour voir :
- Les requêtes réseau
- Les erreurs JavaScript
- Les erreurs CORS

## ✅ Checklist de test complet

- [ ] Backend démarre sans erreur (port 8000)
- [ ] Frontend démarre sans erreur (port 3000)
- [ ] Health check backend fonctionne (http://localhost:8000/health)
- [ ] Interface frontend s'affiche (http://localhost:3000)
- [ ] Upload d'image fonctionne
- [ ] Détection de lettres fonctionne
- [ ] Affichage des résultats fonctionne
- [ ] Pas d'erreurs dans la console du navigateur
- [ ] Pas d'erreurs dans les logs du backend

## 🎯 Commandes rapides

### Démarrer tout en une commande (Windows PowerShell)

```powershell
# Terminal 1
cd StamStam-BE; python -m uvicorn app:app --reload

# Terminal 2 (dans un nouveau terminal)
cd StamStam-FE; npm run dev
```

### Vérifier que tout est actif

```powershell
# Vérifier backend
Invoke-WebRequest -Uri http://localhost:8000/health

# Vérifier frontend
Invoke-WebRequest -Uri http://localhost:3000
```

---

*Si tous les tests passent, l'application est prête pour le déploiement !*

