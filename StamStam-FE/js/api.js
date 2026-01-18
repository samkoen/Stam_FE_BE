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

            const response = await fetch(config.API_URL, {
                method: 'POST',
                body: formData
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
            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new Error(config.MESSAGES.ERROR_NETWORK);
            }
            throw error;
        }
    }

    /**
     * Détecte les lettres dans une image
     * @param {File} file - Fichier image à traiter
     * @returns {Promise<Object>} Résultat avec l'image, les lettres détectées et le nom de la paracha
     */
    static async detectLetters(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(config.API_DETECT_LETTERS, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'שגיאה בזיהוי האותיות');
            }

            const data = await response.json();

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
                paracha: data.paracha || 'לא זוהה',
                text: data.text || '',
                differences: data.differences || []
            };
        } catch (error) {
            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new Error(config.MESSAGES.ERROR_NETWORK);
            }
            throw error;
        }
    }
}

