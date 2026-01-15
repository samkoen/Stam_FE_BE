# Démarrage rapide

## Prérequis

- Node.js (version 16 ou supérieure)
- npm (inclus avec Node.js)

## Installation et lancement

1. **Installer les dépendances** :
   ```bash
   npm install
   ```

2. **Lancer le serveur de développement** :
   ```bash
   npm run dev
   ```

3. **Ouvrir dans le navigateur** :
   - Le serveur démarre automatiquement sur `http://localhost:3000`
   - Le navigateur s'ouvre automatiquement

## Commandes disponibles

- `npm run dev` - Serveur de développement avec hot-reload
- `npm run build` - Construire pour la production
- `npm run preview` - Prévisualiser la version de production
- `npm run serve` - Serveur de prévisualisation sur le port 3000

## Configuration

L'URL de l'API backend peut être modifiée dans `js/config.js` :

```javascript
API_URL: 'http://localhost:8000/api/process-image'
```

Assurez-vous que le backend FastAPI est lancé sur le port 8000 avant d'utiliser l'application.


