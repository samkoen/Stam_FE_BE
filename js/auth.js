/**
 * Module d'authentification — communication avec /api/auth
 */
import { config } from './config.js';

export class AuthApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

async function authFetch(path, options = {}) {
    const url = `${config.API_BASE_URL}${path}`;
    const method = (options.method || 'GET').toUpperCase();
    const headers = { ...(options.headers || {}) };
    if (method !== 'GET' && method !== 'HEAD') {
        headers['Content-Type'] = 'application/json';
    }
    if (config.hfToken) {
        headers['Authorization'] = `Bearer ${config.hfToken}`;
    }
    const res = await fetch(url, {
        ...options,
        credentials: 'include',
        headers,
    });
    if (!res.ok) {
        let detail = 'אירעה שגיאה';
        try {
            const data = await res.json();
            detail = data.detail ?? detail;
        } catch (_) { /* ignore */ }
        throw new AuthApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), res.status);
    }
    if (res.status === 204) return undefined;
    return res.json();
}

export async function registerUser({ email, password, full_name, phone }) {
    return authFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
            email,
            password,
            full_name,
            phone: phone || null,
        }),
    });
}

export async function loginUser({ email, password }) {
    return authFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });
}

export async function logoutUser() {
    return authFetch('/api/auth/logout', { method: 'POST' });
}

export async function getCurrentUser() {
    return authFetch('/api/auth/me');
}

export async function verifyEmailToken(token) {
    const q = `token=${encodeURIComponent(token)}&format=json`;
    return authFetch(`/api/auth/verify-email?${q}`);
}

export async function resendVerificationEmail(email) {
    return authFetch('/api/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
    });
}

export async function sendSupportMessage({ email, message, phone }) {
    return authFetch('/api/auth/support', {
        method: 'POST',
        body: JSON.stringify({
            email,
            message,
            phone: phone || null,
        }),
    });
}

export function saveUserSession(user) {
    localStorage.setItem('stamstam_user_email', user.email);
    localStorage.setItem('stamstam_user_name', user.full_name || '');
}

export function clearUserSession() {
    localStorage.removeItem('stamstam_user_email');
    localStorage.removeItem('stamstam_user_name');
}

export function getStoredEmail() {
    return localStorage.getItem('stamstam_user_email');
}
