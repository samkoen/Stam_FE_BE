/**
 * Configuration de l'application
 */

// Détection de l'environnement
const isProduction = !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1');

// URL par défaut si la variable d'env manque (A REMPLACER PAR VOTRE VRAIE URL HF si nécessaire)
const FALLBACK_PROD_URL = 'http://localhost:8000';

let apiBaseUrl = import.meta.env.VITE_API_URL;
let hfToken = import.meta.env.VITE_HF_TOKEN;


// Debug log pour voir ce qui se passe en prod
console.log('Environment config:', {
    mode: import.meta.env.MODE,
    viteApiUrl: apiBaseUrl,
    isProduction: isProduction,
    hostname: window.location.hostname
});

if (!apiBaseUrl) {
    if (isProduction) {
        console.warn('⚠️ VITE_API_URL non définie en production. Utilisation du fallback:', FALLBACK_PROD_URL);
        apiBaseUrl = FALLBACK_PROD_URL;
    } else {
        apiBaseUrl = 'http://localhost:8000';
    }
}

const API_BASE_URL = apiBaseUrl;
// FORCE PROD URL POUR TEST
//const API_BASE_URL = 'https://samkoen-stam-be.hf.space';

export const config = {
    // URL de l'API backend
    API_URL: `${API_BASE_URL}/api/process-image`,
    API_DETECT_LETTERS: `${API_BASE_URL}/api/detect-letters`,
    
    // Formats de fichiers acceptés
    ACCEPTED_FORMATS: ['image/jpeg', 'image/jpg', 'image/png'],
    
    // Taille maximale du fichier (en MB)
    MAX_FILE_SIZE: 10,
    
    // Messages
    MESSAGES: {
        SELECT_FILE: 'בחר תמונה',
        PROCESSING: 'מנתח...',
        SUCCESS: 'הניתוח הושלם בהצלחה',
        ERROR_UPLOAD: 'שגיאה בהעלאת הקובץ',
        ERROR_PROCESS: 'שגיאה בעיבוד התמונה',
        ERROR_FORMAT: 'פורמט קובץ לא נתמך',
        ERROR_SIZE: 'הקובץ גדול מדי',
        ERROR_NETWORK: 'שגיאת חיבור לשרת'
    },
    
    // Mapping des noms de paracha (latin -> hébreu)
    PARACHA_NAMES: {
        'Chema': 'שמע',
        'Chamoa': 'והיה אם שמע',
        'Kadesh': 'קדש לי כל בכור',
        'Kiyeviaha': 'והיה כי יבאך',
        'Mezuza': 'מזוזה'
    }
};

/**
 * Traduit un nom de paracha du latin vers l'hébreu
 * @param {string} latinName - Nom de la paracha en lettres latines
 * @returns {string} Nom de la paracha en hébreu, ou le nom original si non trouvé
 */
export function translateParachaName(latinName) {
    if (!latinName) return 'לא זוהה';
    return config.PARACHA_NAMES[latinName] || latinName;
}


