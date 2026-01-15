import { config } from './config.js';

/**
 * Module de gestion des fichiers
 */
export class FileHandler {
    /**
     * Valide un fichier
     * @param {File} file - Fichier à valider
     * @returns {Object} { valid: boolean, error?: string }
     */
    static validateFile(file) {
        if (!file) {
            return { valid: false, error: 'לא נבחר קובץ' };
        }

        // Vérifier le format
        if (!config.ACCEPTED_FORMATS.includes(file.type)) {
            return { valid: false, error: config.MESSAGES.ERROR_FORMAT };
        }

        // Vérifier la taille
        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > config.MAX_FILE_SIZE) {
            return { valid: false, error: config.MESSAGES.ERROR_SIZE };
        }

        return { valid: true };
    }

    /**
     * Formate la taille d'un fichier
     * @param {number} bytes - Taille en bytes
     * @returns {string} Taille formatée
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Crée un objet URL pour prévisualiser une image
     * @param {File} file - Fichier image
     * @returns {string} URL de l'image
     */
    static createImagePreview(file) {
        return URL.createObjectURL(file);
    }

    /**
     * Libère une URL d'objet
     * @param {string} url - URL à libérer
     */
    static revokeImagePreview(url) {
        if (url) {
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Télécharge une image depuis une base64
     * @param {string} base64Image - Image en base64
     * @param {string} filename - Nom du fichier
     */
    static downloadImage(base64Image, filename = 'resultat.png') {
        const link = document.createElement('a');
        link.href = `data:image/jpeg;base64,${base64Image}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}


