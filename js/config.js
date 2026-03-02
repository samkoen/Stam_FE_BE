/**
 * Configuration de l'application.
 * VITE_API_URL et VITE_HF_TOKEN : définir dans .env
 */
import { Capacitor } from '@capacitor/core';

const isNativeApp = Capacitor.getPlatform() !== 'web';
const isLocalhost = window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1');

const FALLBACK_PROD_URL = 'https://samkoen-stam-be.hf.space';

let apiBaseUrl = (import.meta.env.VITE_API_URL || '').toString().trim();
let hfToken = (import.meta.env.VITE_HF_TOKEN || '').toString().trim();

// App native (Samsung / Capacitor) : toujours URL prod HTTPS (évite IP locale, localhost, timeouts)
if (isNativeApp) {
    if (!apiBaseUrl || !apiBaseUrl.startsWith('https') || apiBaseUrl.includes('localhost')) {
        apiBaseUrl = FALLBACK_PROD_URL;
    }
} else if (isLocalhost) {
    // Localhost (ex. dev sur :3000) : utiliser VITE_API_URL si défini (Vercel, HF…), sinon backend local :8000
    if (!apiBaseUrl || apiBaseUrl.includes('localhost')) {
        apiBaseUrl = apiBaseUrl || 'http://localhost:8000';
    }
} else if (!apiBaseUrl) {
    apiBaseUrl = FALLBACK_PROD_URL;
}

if (!apiBaseUrl.startsWith('http')) {
    apiBaseUrl = FALLBACK_PROD_URL;
}

const API_BASE_URL = apiBaseUrl.replace(/\/$/, '');

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
