/**
 * Configuration de l'application.
 * En production (Vercel) : définir VITE_API_URL (URL du backend HF) et optionnellement VITE_HF_TOKEN
 * dans les variables d'environnement du projet Vercel, puis redéployer.
 */
// Détection de l'environnement
const isProduction = !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1');

// URL par défaut si la variable d'env manque (A REMPLACER PAR VOTRE VRAIE URL HF si nécessaire)
const FALLBACK_PROD_URL = 'http://localhost:8000';

// VITE_* sont injectées au build par Vite (sur Vercel : définir dans Project Settings > Environment Variables)
let apiBaseUrl = (import.meta.env.VITE_API_URL || '').toString().trim();
let hfToken = (import.meta.env.VITE_HF_TOKEN || '').toString().trim();

// En prod, une URL vide enverrait les requêtes vers le même domaine (FE) → 404. On exige une vraie URL.
if (!apiBaseUrl) {
    if (isProduction) {
        console.warn('⚠️ VITE_API_URL manquante ou vide. Définir sur Vercel l’URL du backend (ex: https://votre-space.hf.space) puis redéployer.');
        apiBaseUrl = FALLBACK_PROD_URL;
    } else {
        apiBaseUrl = 'http://localhost:8000';
    }
}

// Éviter d’utiliser l’origine courante par erreur (pas de URL relative en prod)
if (isProduction && (apiBaseUrl.startsWith('/') || !/^https?:\/\//i.test(apiBaseUrl))) {
    console.warn('⚠️ VITE_API_URL doit être une URL absolue (ex: https://xxx.hf.space). Fallback utilisé.');
    apiBaseUrl = FALLBACK_PROD_URL;
}

const API_BASE_URL = apiBaseUrl.replace(/\/$/, ''); // pas de slash final
// FORCE PROD URL POUR TEST
//const API_BASE_URL = 'https://samkoen-stam-be.hf.space';

export const config = {
    API_BASE_URL,
    hfToken: hfToken || undefined,
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


