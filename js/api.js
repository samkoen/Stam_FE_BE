import { config } from './config.js';

/**
 * Module API pour communiquer avec le backend
 */
export class ApiService {
    /**
     * Traite une image via l'API
     * @param {File} file - Fichier image à traiter
     * @returns {Promise<Object>} Résultat avec l'image traitée
     */
    static async processImage(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            console.log("URL utilisée :", config.API_URL);
            console.log("Token détecté :", config.hfToken ? "OUI" : "NON (Vide)");

            const headers = {};
            if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
            const response = await fetch(config.API_URL, {
                method: 'POST',
                headers,
                body: formData,
                mode: 'cors'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || config.MESSAGES.ERROR_PROCESS);
            }

            const data = await response.json();

            if (!data.success || !data.image) {
                throw new Error(config.MESSAGES.ERROR_PROCESS);
            }

            return {
                success: true,
                image: data.image,
                paracha: data.paracha || 'לא זוהה'
            };
        } catch (error) {
            if (isNetworkError(error)) throw new Error(config.MESSAGES.ERROR_NETWORK);
            throw error;
        }
    }

    /**
     * Détecte les lettres dans une image
     * @param {File} file - Fichier image à traiter
     * @param {string} email - Email de l'utilisateur
     * @returns {Promise<Object>} Résultat avec l'image, les lettres détectées et le nom de la paracha
     */
    static async detectLetters(file, email) {
        const url = config.API_DETECT_LETTERS;
        try {
            if (!email || !email.includes('@')) {
                throw new Error('אימייל לא תקין');
            }
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('email', email);

            const headers = {};
            if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
            try {
                const { Capacitor } = await import('@capacitor/core');
                if (Capacitor.getPlatform() !== 'web') headers['X-Want-B64'] = 'true';
            } catch (_) {}

            console.log('[StamStam] POST', url);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000);
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: formData,
                mode: 'cors',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const rawBytes = await response.arrayBuffer();
            let data = JSON.parse(new TextDecoder('utf-8').decode(rawBytes));
            if (data.body_b64) {
                const bin = atob(data.body_b64);
                const bytes = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                data = JSON.parse(new TextDecoder('utf-8').decode(bytes));
            }

            if (!response.ok) {
                const errorData = data || {};
                throw new Error(errorData.detail || 'שגיאה בזיהוי האותיות');
            }

            if (!data.success || !data.image) {
                throw new Error('שגיאה בזיהוי האותיות');
            }

            // Log pour déboguer
            console.log('Réponse API detectLetters:', {
                success: data.success,
                hasImage: !!data.image,
                paracha: data.paracha,
                text: data.text,
                textLength: data.text ? data.text.length : 0
            });

            return {
                success: true,
                image: data.image,
                imageErrorsOnly: data.image_errors_only || null,
                paracha: data.paracha || 'לא זוהה',
                text: data.text || '',
                differences: data.differences || [],
                parachaStatus: data.paracha_status || null,
                hasErrors: data.has_errors ?? null,
                errors: data.errors || null,
                confusableAccepted: data.confusable_accepted || []
            };
        } catch (error) {
            console.error('[StamStam] detectLetters error:', error?.message, error);
            if (isNetworkError(error)) throw new Error(config.MESSAGES.ERROR_NETWORK);
            throw error;
        }
    }

    /**
     * Télécharge un rapport PDF
     * @param {Object} data - { image_errors_only, paracha, paracha_status, differences }
     * @returns {Promise<Blob>} Le fichier PDF
     */
    static async exportPdf(data) {
        const url = config.API_EXPORT_PDF;
        const headers = { 'Content-Type': 'application/json' };
        if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
        const payload = {
            image_errors_only: data.image_errors_only || '',
            paracha: data.paracha || '',
            paracha_status: data.paracha_status || '',
            differences: data.differences || [],
            errors: data.errors || null,
            has_errors: data.has_errors
        };
        let body;
        try {
            const { Capacitor } = await import('@capacitor/core');
            if (Capacitor.getPlatform() !== 'web') {
                const utf8 = new TextEncoder().encode(JSON.stringify(payload));
                let b64 = '';
                const chunk = 8192;
                for (let i = 0; i < utf8.length; i += chunk) {
                    b64 += String.fromCharCode(...utf8.subarray(i, i + chunk));
                }
                body = JSON.stringify({ payload_b64: btoa(b64) });
            } else {
                body = JSON.stringify(payload);
            }
        } catch (_) {
            body = JSON.stringify(payload);
        }
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body,
            mode: 'cors'
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'שגיאה בהורדת הדוח');
        }
        return response.blob();
    }
}

function isNetworkError(error) {
    if (error instanceof TypeError) return true;
    if (error?.name === 'AbortError') return true;
    const msg = (error?.message || '').toLowerCase();
    return msg.includes('fetch') || msg.includes('network') || msg.includes('failed to load') || msg.includes('aborted');
}

