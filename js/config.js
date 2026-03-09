/**
 * Configuration de l'application.
 * VITE_API_URL et VITE_HF_TOKEN : définir dans .env
 * Choix serveur API : voir api-server-selection.js (localhost → local, app → HF).
 */
import { getApiBaseUrl } from './api-server-selection.js';

let hfToken = (import.meta.env.VITE_HF_TOKEN || '').toString().trim();
const API_BASE_URL = getApiBaseUrl((import.meta.env.VITE_API_URL || '').toString().trim());

if (typeof console !== 'undefined') {
    console.log('[StamStam] API:', API_BASE_URL, 'token:', !!hfToken);
}

export const config = {
    API_BASE_URL,
    hfToken: hfToken || undefined,
    API_URL: `${API_BASE_URL}/api/process-image`,
    API_DETECT_LETTERS: `${API_BASE_URL}/api/detect-letters`,
    API_EXPORT_PDF: `${API_BASE_URL}/api/export-pdf`,
    
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
        ERROR_NETWORK: 'שגיאת חיבור לשרת',
        IMAGE_QUALITY_WARNING: 'התמונה בעייתית (אינה ברורה מספיק או חתוכה בצורה לא טובה). אנא צלם שוב תמונה ברורה וישרה.'
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
