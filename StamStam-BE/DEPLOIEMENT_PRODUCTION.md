# Guide de déploiement en production

Ce guide explique comment déployer l'application StamStam en production.

## Prérequis

- Python 3.8+
- Gunicorn installé (`pip install gunicorn`)
- Variables d'environnement configurées (voir `ENV_EXAMPLE.txt`)

## Installation des dépendances

```bash
cd StamStam-BE
pip install -r requirements.txt
```

## Configuration

1. **Copier le fichier d'exemple** :
   ```bash
   cp ENV_EXAMPLE.txt .env
   ```

2. **Modifier `.env`** avec vos valeurs de production :
   ```bash
   STAMSTAM_ENV=prod
   STAMSTAM_DEBUG=false
   STAMSTAM_MODEL_PATH=/chemin/absolu/vers/model.hdf5
   STAMSTAM_OVERFLOW_DIR=/chemin/absolu/vers/overflow
   STAMSTAM_CORS_ORIGINS=https://votre-domaine.com
   STAMSTAM_HOST=0.0.0.0
   STAMSTAM_PORT=8000
   ```

## Démarrage en production

### Option 1 : Script Python (recommandé - multiplateforme)

```bash
python start_production.py
```

Le script vérifie automatiquement :
- Les variables d'environnement
- L'existence du modèle ML
- L'existence du dossier overflow
- La présence de Gunicorn

### Option 2 : Script Bash (Linux/Mac)

```bash
chmod +x start_production.sh
./start_production.sh
```

### Option 3 : Commande Gunicorn directe

```bash
gunicorn --config gunicorn_config.py app:app
```

### Option 4 : Avec variables d'environnement explicites

```bash
export STAMSTAM_ENV=prod
export STAMSTAM_DEBUG=false
export STAMSTAM_MODEL_PATH=/chemin/vers/model.hdf5
export STAMSTAM_OVERFLOW_DIR=/chemin/vers/overflow
gunicorn --config gunicorn_config.py app:app
```

## Configuration Gunicorn

Le fichier `gunicorn_config.py` contient la configuration du serveur :

- **Workers** : Nombre de workers (auto-détecté selon CPU, max 4 pour éviter la surcharge mémoire)
- **Timeout** : 120 secondes (peut être long pour le traitement ML)
- **Port** : Configuré via `STAMSTAM_PORT` (défaut: 8000)
- **Host** : Configuré via `STAMSTAM_HOST` (défaut: 0.0.0.0)

### Ajuster le nombre de workers

```bash
export STAMSTAM_WORKERS=2  # Pour un serveur avec peu de RAM
gunicorn --config gunicorn_config.py app:app
```

## Démarrage avec systemd (Linux)

Créez un fichier `/etc/systemd/system/stamstam-api.service` :

```ini
[Unit]
Description=StamStam API FastAPI
After=network.target

[Service]
Type=notify
User=stamstam
Group=stamstam
WorkingDirectory=/path/to/StamStam-BE
Environment="STAMSTAM_ENV=prod"
Environment="STAMSTAM_DEBUG=false"
Environment="STAMSTAM_MODEL_PATH=/path/to/model.hdf5"
Environment="STAMSTAM_OVERFLOW_DIR=/path/to/overflow"
Environment="STAMSTAM_CORS_ORIGINS=https://votre-domaine.com"
ExecStart=/usr/bin/python3 /path/to/StamStam-BE/start_production.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Puis :

```bash
sudo systemctl daemon-reload
sudo systemctl enable stamstam-api
sudo systemctl start stamstam-api
sudo systemctl status stamstam-api
```

## Démarrage avec supervisor

Créez un fichier `/etc/supervisor/conf.d/stamstam-api.conf` :

```ini
[program:stamstam-api]
command=/path/to/venv/bin/gunicorn --config gunicorn_config.py app:app
directory=/path/to/StamStam-BE
user=stamstam
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/stamstam-api.log
environment=STAMSTAM_ENV="prod",STAMSTAM_DEBUG="false"
```

Puis :

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start stamstam-api
```

## Health Check

Vérifier que l'API fonctionne :

```bash
curl http://localhost:8000/health
```

Réponse attendue :

```json
{
  "status": "healthy",
  "model_path_exists": true,
  "overflow_dir_exists": true,
  "environment": "prod"
}
```

## Logs

Les logs sont configurés via les variables d'environnement :

- `STAMSTAM_LOG_FILE` : Fichier de log (vide = stdout uniquement)
- `STAMSTAM_LOG_LEVEL` : Niveau de log (DEBUG, INFO, WARNING, ERROR)
- `STAMSTAM_ACCESS_LOG` : Log d'accès Gunicorn (défaut: stdout)
- `STAMSTAM_ERROR_LOG` : Log d'erreur Gunicorn (défaut: stderr)

Exemple :

```bash
export STAMSTAM_LOG_FILE=/var/log/stamstam.log
export STAMSTAM_ACCESS_LOG=/var/log/stamstam-access.log
export STAMSTAM_ERROR_LOG=/var/log/stamstam-error.log
```

## Monitoring

### Vérifier les processus Gunicorn

```bash
ps aux | grep gunicorn
```

### Vérifier les ports ouverts

```bash
netstat -tulpn | grep :8000
# ou
ss -tulpn | grep :8000
```

### Tester l'API

```bash
# Health check
curl http://localhost:8000/health

# Test endpoint principal
curl http://localhost:8000/
```

## Dépannage

### L'API ne démarre pas

1. Vérifier les logs : `tail -f /var/log/stamstam-error.log`
2. Vérifier les variables d'environnement : `env | grep STAMSTAM`
3. Vérifier que le modèle ML existe : `ls -la $STAMSTAM_MODEL_PATH`
4. Vérifier que le dossier overflow existe : `ls -la $STAMSTAM_OVERFLOW_DIR`

### Erreur "Module not found"

```bash
# S'assurer d'être dans le bon répertoire
cd /path/to/StamStam-BE

# Vérifier les dépendances
pip install -r requirements.txt
```

### Erreur "Permission denied"

```bash
# Donner les permissions d'exécution au script
chmod +x start_production.sh
chmod +x start_production.py
```

### Le serveur est trop lent

- Réduire le nombre de workers : `export STAMSTAM_WORKERS=1`
- Augmenter le timeout : `export STAMSTAM_TIMEOUT=180`
- Vérifier les ressources serveur (CPU, RAM)

## Mise à jour de l'application

1. Arrêter le service :
   ```bash
   sudo systemctl stop stamstam-api
   # ou
   sudo supervisorctl stop stamstam-api
   ```

2. Mettre à jour le code :
   ```bash
   git pull
   pip install -r requirements.txt
   ```

3. Redémarrer :
   ```bash
   sudo systemctl start stamstam-api
   # ou
   sudo supervisorctl start stamstam-api
   ```

---

*Dernière mise à jour : [Date]*
*Projet : StamStam - Déploiement Production*

