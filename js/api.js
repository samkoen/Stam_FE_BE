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

            const response = await fetch(config.API_URL, {
                method: 'POST',
                headers: {
                    // On ajoute le Token ici
                    'Authorization': `Bearer ${config.hfToken}`
                },
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
        try {
            if (!email || !email.includes('@')) {
                throw new Error('אימייל לא תקין');
            }
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('email', email);

            const headers = {};
            if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;

            const response = await fetch(config.API_DETECT_LETTERS, {
                method: 'POST',
                headers,
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
                differences: data.differences || [],
                parachaStatus: data.paracha_status || null,
                hasErrors: data.has_errors ?? null,
                errors: data.errors || null,
                confusableAccepted: data.confusable_accepted || []
            };
        } catch (error) {
            if (isNetworkError(error)) throw new Error(config.MESSAGES.ERROR_NETWORK);
            throw error;
        }
    }

    /**
     * Demande de connexion : si l'email est déjà connu, pas de code ; sinon envoie un code.
     * @param {string} email - Email du compte
     * @returns {Promise<{ success: boolean, requiresCode: boolean, email?: string }>}
     */
    static async requestLogin(email) {
        const response = await fetch(config.API_AUTH_REQUEST_LOGIN, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email.trim().toLowerCase() })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = parseDetail(data.detail);
            console.warn('requestLogin error', response.status, data);
            throw new Error(detail || 'שגיאה בהתחברות');
        }
        return { success: true, requiresCode: data.requiresCode, email: data.email };
    }

    /**
     * Envoie un code de vérification à l'email de l'utilisateur (auth par email).
     * @param {string} email - Email du compte
     * @returns {Promise<{ success: boolean }>}
     */
    static async sendAuthCode(email) {
        const response = await fetch(config.API_AUTH_SEND_CODE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email.trim().toLowerCase() })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = parseDetail(data.detail);
            console.warn('sendAuthCode error', response.status, data);
            throw new Error(detail || 'שגיאה בשליחת הקוד');
        }
        return { success: true, message: data.message };
    }

    /**
     * Vérifie le code saisi et authentifie l'utilisateur.
     * @param {string} email - Email du compte
     * @param {string} code - Code reçu par email
     * @returns {Promise<{ success: boolean, email: string }>}
     */
    static async verifyAuthCode(email, code) {
        const response = await fetch(config.API_AUTH_VERIFY_CODE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email.trim().toLowerCase(), code: (code || '').trim() })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = parseDetail(data.detail);
            throw new Error(detail || 'קוד לא תקין או שפג תוקף');
        }
        return { success: true, email: data.email };
    }
}

/** FastAPI peut renvoyer detail en string ou en liste de { msg } */
function parseDetail(detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0 && detail[0].msg) return detail[0].msg;
    if (Array.isArray(detail) && detail.length > 0 && detail[0].loc) return detail.map(d => d.msg || JSON.stringify(d)).join(', ');
    return null;
}

function isNetworkError(error) {
    if (error instanceof TypeError) return true;
    const msg = (error?.message || '').toLowerCase();
    return msg.includes('fetch') || msg.includes('network') || msg.includes('failed to load');
}

