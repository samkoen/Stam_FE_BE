/**
 * Choix du serveur API — NE PAS MODIFIER sauf changement d’URL HF ou de port local.
 * Règle : localhost (ex. :3000) → serveur local ; appli native (Capacitor) → HF.
 */
import { Capacitor } from '@capacitor/core';

const HF_SERVER_URL = 'https://samkoen-stam-be.hf.space';
const LOCAL_SERVER_DEFAULT = 'http://localhost:8000';

let platform = 'web';
try {
    platform = Capacitor.getPlatform();
} catch (_) {}

const isNativeApp = platform !== 'web';
const isLocalhost = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === ''
);

/**
 * Retourne l’URL de base de l’API selon le contexte.
 * @param {string} envApiUrl - VITE_API_URL (optionnel)
 * @returns {string}
 */
export function getApiBaseUrl(envApiUrl = '') {
    const u = (envApiUrl || '').toString().trim();
    if (isNativeApp) return HF_SERVER_URL.replace(/\/$/, '');
    if (isLocalhost) {
        const lower = u.toLowerCase();
        if (lower.startsWith('http://localhost') || lower.startsWith('http://127.0.0.1'))
            return u.replace(/\/$/, '');
        return LOCAL_SERVER_DEFAULT;
    }
    if (u.startsWith('http')) {
        const base = u.replace(/\/$/, '');
        if (typeof window !== 'undefined' && window.location?.origin && base === window.location.origin) {
            console.warn('[StamStam] VITE_API_URL pointe vers l\'app (même origine). Utilisation du serveur HF.');
            return HF_SERVER_URL.replace(/\/$/, '');
        }
        return base;
    }
    return HF_SERVER_URL.replace(/\/$/, '');
}
