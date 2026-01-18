# Configuration du Logging

## Emplacement des logs

### En développement (par défaut)
Les logs sont écrits dans **deux endroits** :

1. **Console/Terminal (stdout)** : Tous les logs sont affichés dans la console
2. **Fichier de log** : `StamStam-BE/logs/stamstam.log` (créé automatiquement)

### En production
Par défaut, les logs sont **uniquement dans la console** (stdout). C'est recommandé car :
- Les logs sont gérés par le système (systemd, Docker, etc.)
- Pas de problème de permissions
- Pas de risque de remplir le disque
- Les logs peuvent être redirigés vers un système centralisé (ELK, etc.)

Pour activer un fichier de log en production, définissez `STAMSTAM_LOG_FILE`.

## Configuration via variables d'environnement

Vous pouvez personnaliser le comportement du logging avec des variables d'environnement :

### `STAMSTAM_ENV`
Définit l'environnement : `prod`/`production`/`pro` pour la production, ou autre chose pour le développement.

**Exemples :**
```bash
# Production
export STAMSTAM_ENV=prod

# Développement (par défaut si non défini)
export STAMSTAM_ENV=dev
```

### `STAMSTAM_DEBUG`
Active le mode DEBUG (logs très détaillés).

**Exemples :**
```bash
# Windows PowerShell
$env:STAMSTAM_DEBUG="true"

# Windows CMD
set STAMSTAM_DEBUG=true

# Linux/Mac
export STAMSTAM_DEBUG=true
```

### `STAMSTAM_LOG_FILE`
Spécifie un fichier de log personnalisé. Si non défini :
- **Développement** : `logs/stamstam.log` (créé automatiquement)
- **Production** : Aucun fichier (logs uniquement dans stdout)

**Exemples :**
```bash
# Windows PowerShell
$env:STAMSTAM_LOG_FILE="C:\logs\stamstam.log"

# Windows CMD
set STAMSTAM_LOG_FILE=C:\logs\stamstam.log

# Linux/Mac (emplacement standard pour les logs système)
export STAMSTAM_LOG_FILE=/var/log/stamstam.log
```

## Désactiver le fichier de log

Pour désactiver l'écriture dans un fichier et garder uniquement la console :

```bash
# Option 1 : Définir à "none" ou "false"
export STAMSTAM_LOG_FILE="none"

# Option 2 : Mettre en production (désactive automatiquement)
export STAMSTAM_ENV=prod
```

## Gestion des erreurs

Si le système ne peut pas écrire dans le fichier de log (permissions, espace disque, etc.) :
- ✅ L'application **continue de fonctionner** normalement
- ✅ Les logs sont **toujours affichés dans la console**
- ⚠️ Un avertissement est affiché pour indiquer le problème
- ❌ L'application **ne plante pas** si l'écriture dans le fichier échoue

## Format des logs

### Mode normal (INFO)
```
2024-01-15 10:30:45 - BE_Model_Cursor.comparison.text_alignment - INFO - Alignement terminé
```

### Mode DEBUG
```
2024-01-15 10:30:45 - BE_Model_Cursor.comparison.text_alignment - DEBUG - [text_alignment.py:328] - Alignement terminé
```

## Niveaux de log

- **DEBUG** : Informations détaillées pour le débogage
- **INFO** : Informations générales sur le fonctionnement
- **WARNING** : Avertissements (problèmes non critiques)
- **ERROR** : Erreurs qui nécessitent une attention

## Rotation des logs

Pour l'instant, les logs sont écrits dans un seul fichier. Pour la production, vous pouvez :

1. Utiliser un outil externe de rotation (logrotate sur Linux)
2. Configurer Python logging avec `RotatingFileHandler` (à implémenter si nécessaire)

## Exemple d'utilisation dans le code

```python
from BE_Model_Cursor.utils.logger import get_logger

logger = get_logger(__name__, debug=True)

logger.debug("Message de debug")
logger.info("Message d'information")
logger.warning("Avertissement")
logger.error("Erreur")
```

