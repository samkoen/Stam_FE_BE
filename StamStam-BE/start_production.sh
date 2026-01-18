#!/bin/bash
# Script de démarrage pour la production
# Utilise Gunicorn avec des workers Uvicorn pour FastAPI

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Démarrage de StamStam API en production ===${NC}"

# Vérifier que les variables d'environnement nécessaires sont définies
if [ -z "$STAMSTAM_ENV" ]; then
    echo -e "${YELLOW}⚠️  STAMSTAM_ENV non défini, utilisation de 'prod' par défaut${NC}"
    export STAMSTAM_ENV=prod
fi

# Charger les variables d'environnement depuis .env si le fichier existe
if [ -f .env ]; then
    echo -e "${GREEN}📄 Chargement des variables depuis .env${NC}"
    set -a
    source .env
    set +a
fi

# Vérifier que le modèle ML existe
if [ ! -f "$STAMSTAM_MODEL_PATH" ]; then
    echo -e "${RED}❌ ERREUR: Le fichier de modèle n'existe pas: $STAMSTAM_MODEL_PATH${NC}"
    exit 1
fi

# Vérifier que le dossier overflow existe
if [ ! -d "$STAMSTAM_OVERFLOW_DIR" ]; then
    echo -e "${RED}❌ ERREUR: Le dossier overflow n'existe pas: $STAMSTAM_OVERFLOW_DIR${NC}"
    exit 1
fi

# Afficher la configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  Environment: $STAMSTAM_ENV"
echo "  Host: ${STAMSTAM_HOST:-0.0.0.0}"
echo "  Port: ${STAMSTAM_PORT:-8000}"
echo "  Workers: ${STAMSTAM_WORKERS:-auto}"
echo "  Model: $STAMSTAM_MODEL_PATH"
echo "  Overflow: $STAMSTAM_OVERFLOW_DIR"

# Démarrer Gunicorn
echo -e "${GREEN}🚀 Démarrage de Gunicorn...${NC}"

exec gunicorn \
    --config gunicorn_config.py \
    app:app

