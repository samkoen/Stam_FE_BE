/**
 * Page de vérification d'e-mail
 */
import { verifyEmailToken, AuthApiError } from './auth.js';

const params = new URLSearchParams(window.location.search);
const token = params.get('token') || '';
const statusEl = document.getElementById('statusMessage');
const loginLink = document.getElementById('loginLink');

window.addEventListener('DOMContentLoaded', async () => {
    if (!token) {
        setError('קישור האימות חסר');
        return;
    }
    try {
        const res = await verifyEmailToken(token);
        if (res.already_verified) {
            setSuccess('האימייל כבר אומת. ניתן להתחבר.');
        } else {
            setSuccess('האימייל אומת בהצלחה! כעת ניתן להתחבר.');
        }
    } catch (err) {
        setError(err instanceof AuthApiError ? err.message : 'שגיאה באימות');
    }
});

function setSuccess(message) {
    statusEl.textContent = message;
    statusEl.className = 'status-message success';
    loginLink.style.display = 'inline-block';
}

function setError(message) {
    statusEl.textContent = message;
    statusEl.className = 'status-message error';
}
