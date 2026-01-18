"""
Configuration Gunicorn pour le serveur FastAPI en production.
Gunicorn utilise des workers Uvicorn pour FastAPI.
"""
import multiprocessing
import os

# Nom de l'application (module:variable)
bind = f"{os.getenv('STAMSTAM_HOST', '0.0.0.0')}:{os.getenv('STAMSTAM_PORT', '8000')}"

# Nombre de workers
# Formule recommandée : (2 × CPU cores) + 1
# Mais pour FastAPI/ML, on peut réduire car le modèle ML est partagé
cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv('STAMSTAM_WORKERS', cpu_count + 1))
# Limiter à 4 workers max pour éviter la surcharge mémoire avec le modèle ML
if workers > 4:
    workers = 4

# Type de worker (Uvicorn pour FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = int(os.getenv('STAMSTAM_TIMEOUT', '120'))  # 2 minutes (peut être long pour le traitement ML)
keepalive = 30

# Logging
accesslog = os.getenv('STAMSTAM_ACCESS_LOG', '-')  # '-' = stdout
errorlog = os.getenv('STAMSTAM_ERROR_LOG', '-')    # '-' = stderr
loglevel = os.getenv('STAMSTAM_LOG_LEVEL', 'info').lower()

# Limiter les workers si trop de CPU
max_requests = int(os.getenv('STAMSTAM_MAX_REQUESTS', '1000'))  # Recycler les workers après N requêtes
max_requests_jitter = 50

# Préchargement de l'application (améliore les performances mais augmente l'utilisation mémoire)
preload_app = False  # Désactivé car le modèle ML est lourd - charger à la demande

# Nom du processus
proc_name = 'stamstam-api'

# Mode de démarrage
daemon = False  # Ne pas démoniser (géré par systemd/supervisor)

# User/Group (à définir par le gestionnaire de processus)
# user = 'stamstam'
# group = 'stamstam'

# Répertoire de travail
chdir = os.path.dirname(os.path.abspath(__file__))

# Variables d'environnement
# Toutes les variables STAMSTAM_* seront passées par l'environnement

