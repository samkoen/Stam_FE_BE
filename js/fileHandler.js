import { config } from './config.js';
import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';

/**
 * Nettoie la chaîne base64 (préfixe data URL, espaces)
 */
function cleanBase64(str) {
    if (typeof str !== 'string') return '';
    let s = str.trim();
    if (s.includes(',')) s = s.split(',')[1] || s;
    return s.replace(/\s/g, '');
}

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
     * Convertit un File en copie en mémoire (évite les problèmes d'envoi sur Android WebView
     * quand le File vient du sélecteur de fichiers / content://)
     * @param {File} file
     * @returns {Promise<File>}
     */
    static async fileToInMemory(file) {
        const buf = await file.arrayBuffer();
        return new File([buf], file.name, { type: file.type, lastModified: Date.now() });
    }

    /**
     * Crée une URL d'affichage pour une image base64.
     * Sur Android WebView, les data URLs échouent souvent → on écrit en fichier et utilise convertFileSrc.
     * @param {string} base64 - Image en base64 (avec ou sans préfixe data:)
     * @returns {Promise<string>} URL utilisable dans img.src
     */
    static async base64ToDisplayUrl(base64) {
        const raw = cleanBase64(base64);
        if (!raw) return '';

        const isNative = Capacitor.getPlatform() !== 'web';
        if (isNative) {
            const path = `display_${Date.now()}.jpg`;
            const { uri } = await Filesystem.writeFile({
                path,
                data: raw,
                directory: Directory.Cache
            });
            return Capacitor.convertFileSrc(uri);
        }
        return `data:image/jpeg;base64,${raw}`;
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
     * Libère une URL d'objet (blob uniquement, pas les data URL)
     * @param {string} url - URL à libérer
     */
    static revokeImagePreview(url) {
        if (url && url.startsWith('blob:')) {
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


