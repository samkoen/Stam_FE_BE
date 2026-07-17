import { config } from './config.js';

/** Promise wake en cours (déduplique les pings parallèles). */
let wakePromise = null;
/** Timestamp du dernier wake réussi. */
let wakeDoneAt = 0;

/**
 * Module API pour communiquer avec le backend
 */
export class ApiService {
    /**
     * Ping léger pour réveiller le Space HF (GPU en pause).
     * Fire-and-forget OK ; aussi awaitable avant בדוק.
     * @returns {Promise<boolean>} true si le serveur a répondu
     */
    static wakeUpServer() {
        const ttl = config.WAKE_TTL_MS || 300000;
        if (wakePromise) return wakePromise;
        if (wakeDoneAt && Date.now() - wakeDoneAt < ttl) {
            return Promise.resolve(true);
        }
        wakePromise = pingHealth()
            .then((ok) => {
                if (ok) wakeDoneAt = Date.now();
                return ok;
            })
            .finally(() => {
                wakePromise = null;
            });
        return wakePromise;
    }

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
     * @param {string} [forcedReference] - chema | chamoa | kadesh | kiyeviaha | mezuza | esther | torah
     * @param {string|null} [inferenceResumeToken] - jeton 1er POST (needs_manual_reference)
     */
    static async detectLetters(file, email, forcedReference = null, inferenceResumeToken = null) {
        if (!email || !email.includes('@')) {
            throw new Error('אימייל לא תקין');
        }
        // Attendre un wake déjà lancé (photo) ou en déclencher un
        await ApiService.wakeUpServer();
        try {
            return await postDetectLetters(file, email, forcedReference, inferenceResumeToken);
        } catch (error) {
            if (!isNetworkError(error)) throw error;
            // 1 retry après nouveau ping (cold start HF)
            wakeDoneAt = 0;
            await ApiService.wakeUpServer();
            try {
                return await postDetectLetters(file, email, forcedReference, inferenceResumeToken);
            } catch (retryErr) {
                console.error('[StamStam] detectLetters retry error:', retryErr?.message, retryErr);
                if (isNetworkError(retryErr)) {
                    throw new Error(config.MESSAGES.ERROR_SERVER_WAKING || config.MESSAGES.ERROR_NETWORK);
                }
                throw retryErr;
            }
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

async function pingHealth() {
    const url = config.API_HEALTH || `${config.API_BASE_URL}/health`;
    const headers = {};
    if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
    const controller = new AbortController();
    const timeoutMs = config.WAKE_TIMEOUT_MS || 180000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        console.log('[StamStam] wake-up GET', url);
        const res = await fetch(url, {
            method: 'GET',
            headers,
            mode: 'cors',
            cache: 'no-store',
            signal: controller.signal,
        });
        // Toute réponse HTTP = Space joignable (même 503 pendant boot modèle)
        return res.status > 0;
    } catch (err) {
        console.warn('[StamStam] wake-up failed:', err?.message || err);
        return false;
    } finally {
        clearTimeout(timeoutId);
    }
}

async function postDetectLetters(file, email, forcedReference, inferenceResumeToken) {
    const url = config.API_DETECT_LETTERS;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('email', email);
    if (forcedReference && String(forcedReference).trim()) {
        formData.append('forced_reference', String(forcedReference).trim().toLowerCase());
        const tok = inferenceResumeToken && String(inferenceResumeToken).trim();
        if (tok) formData.append('inference_resume_token', tok);
    }

    const headers = {};
    if (config.hfToken) headers['Authorization'] = `Bearer ${config.hfToken}`;
    try {
        const { Capacitor } = await import('@capacitor/core');
        if (Capacitor.getPlatform() !== 'web') headers['X-Want-B64'] = 'true';
    } catch (_) { /* web */ }

    console.log('[StamStam] POST', url);
    const controller = new AbortController();
    const timeoutMs = config.DETECT_TIMEOUT_MS || 300000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
        response = await fetch(url, {
            method: 'POST',
            headers,
            body: formData,
            mode: 'cors',
            signal: controller.signal,
        });
    } finally {
        clearTimeout(timeoutId);
    }

    const rawBytes = await response.arrayBuffer();
    let data = JSON.parse(new TextDecoder('utf-8').decode(rawBytes));
    let pdfBase64 = null;
    if (data.body_b64) {
        pdfBase64 = data.pdf_b64 || null;
        const bin = atob(data.body_b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        data = JSON.parse(new TextDecoder('utf-8').decode(bytes));
    }

    if (!response.ok) {
        throw new Error((data && data.detail) || 'שגיאה בזיהוי האותיות');
    }
    if (!data.success || !data.image) {
        throw new Error('שגיאה בזיהוי האותיות');
    }

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
        confusableAccepted: data.confusable_accepted || [],
        letterZones: data.letter_zones || [],
        pdfBase64,
        needsManualReference: !!data.needs_manual_reference,
        inferenceResumeToken: data.inference_resume_token || null,
        supportAllText: data.support_all_text !== false,
        referenceUserMismatch: !!data.reference_user_mismatch,
    };
}

function isNetworkError(error) {
    if (error instanceof TypeError) return true;
    if (error?.name === 'AbortError') return true;
    const msg = (error?.message || '').toLowerCase();
    return msg.includes('fetch') || msg.includes('network') || msg.includes('failed to load') || msg.includes('aborted');
}
