import { config } from './config.js';
import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

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
     * Tourne une image de 90° (horaire par défaut).
     * @param {File|Blob} file
     * @param {boolean} clockwise
     * @returns {Promise<File>}
     */
    static async rotateImage90(file, clockwise = true) {
        const bitmap = await createImageBitmap(file);
        const canvas = document.createElement('canvas');
        const w = bitmap.width;
        const h = bitmap.height;
        canvas.width = h;
        canvas.height = w;
        const ctx = canvas.getContext('2d');
        if (clockwise) {
            ctx.translate(h, 0);
            ctx.rotate(Math.PI / 2);
        } else {
            ctx.translate(0, w);
            ctx.rotate(-Math.PI / 2);
        }
        ctx.drawImage(bitmap, 0, 0);
        bitmap.close();
        const blob = await new Promise((resolve, reject) => {
            canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('rotate failed'))), 'image/jpeg', 0.92);
        });
        const name = (file.name || 'image.jpg').replace(/\.[^.]+$/, '') + '.jpg';
        return new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() });
    }

    /**
     * URL d'affichage pour un File (WebView native → fichier cache).
     * @param {File} file
     * @returns {Promise<string>}
     */
    static async fileToDisplayUrl(file) {
        let platform = 'web';
        try { platform = Capacitor.getPlatform(); } catch (_) { /* ignore */ }
        if (platform !== 'web') {
            const buf = await file.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let binary = '';
            for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
            return FileHandler.base64ToDisplayUrl(btoa(binary));
        }
        return FileHandler.createImagePreview(file);
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

    /**
     * En app native : enregistre le PDF en cache et ouvre le partage pour que l'utilisateur
     * choisisse où le sauver (Téléchargements, Drive, etc.).
     * @param {Blob} blob - PDF en blob
     * @param {string} filename - Nom du fichier (ex. rapport-stam.pdf)
     * @returns {Promise<void>}
     */
    static async saveAndSharePdf(blob, filename = 'rapport-stam.pdf') {
        const buf = await blob.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let binary = '';
        const chunk = 8192;
        for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
        }
        const base64 = btoa(binary);
        await Filesystem.writeFile({
            path: filename,
            data: base64,
            directory: Directory.Cache
        });
        const { uri } = await Filesystem.getUri({ directory: Directory.Cache, path: filename });
        await Share.share({
            title: filename,
            url: uri,
            dialogTitle: 'שמור PDF'
        });
    }
}


