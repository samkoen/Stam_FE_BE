# StamStam Frontend


Frontend moderne et modulaire pour l'application de vérification de Paracha.

## Structure du projet

```
StamStam-FE/
├── index.html          # Point d'entrée HTML
├── package.json        # Configuration npm
├── vite.config.js      # Configuration Vite
├── css/
│   ├── main.css       # Styles principaux et variables CSS
│   └── components.css # Styles des composants
├── js/
│   ├── main.js        # Application principale
│   ├── config.js      # Configuration de l'application
│   ├── api.js         # Service API pour communiquer avec le backend
│   ├── fileHandler.js # Gestion des fichiers
│   └── ui.js          # Gestion de l'interface utilisateur
└── README.md          # Documentation
```

## Architecture

### Modules JavaScript

- **main.js** : Point d'entrée de l'application, orchestre tous les modules
- **config.js** : Configuration centralisée (URLs, messages, etc.)
- **api.js** : Service pour les appels API au backend
- **fileHandler.js** : Validation et manipulation des fichiers
- **ui.js** : Gestion de l'interface utilisateur et des interactions

### CSS

- **main.css** : Variables CSS, reset, styles de base
- **components.css** : Styles des composants réutilisables

## Fonctionnalités

- ✅ Upload de fichiers par clic ou drag & drop
- ✅ Validation des fichiers (format, taille)
- ✅ Interface de chargement avec animations
- ✅ Affichage des résultats avec légende
- ✅ Gestion des erreurs avec messages clairs
- ✅ Téléchargement de l'image résultat
- ✅ Design responsive et moderne
- ✅ Animations et transitions fluides

## Installation

1. Installer les dépendances :
   ```bash
   npm install
   ```

## Utilisation

### Mode développement

Lancer le serveur de développement avec hot-reload :

```bash
npm run dev
```

Le serveur démarre sur `http://localhost:3000` et s'ouvre automatiquement dans le navigateur.

### Mode production

Construire l'application pour la production :

```bash
npm run build
```

Prévisualiser la version de production :

```bash
npm run preview
```

### Autres options

- `npm run serve` : Lance le serveur de prévisualisation sur le port 3000

## Configuration

Modifier l'URL de l'API dans `js/config.js` :

```javascript
export const config = {
    API_URL: 'http://localhost:8000/api/process-image',
    // ...
};
```

## Compatibilité

- Navigateurs modernes (Chrome, Firefox, Safari, Edge)
- Support des modules ES6
- Responsive design (mobile, tablette, desktop)

