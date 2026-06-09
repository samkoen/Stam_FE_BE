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
    const res = await fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
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
    return authFetch(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
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
