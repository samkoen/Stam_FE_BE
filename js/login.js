/**
 * Module de gestion de la page de login
 */
import { loginUser, getStoredEmail, saveUserSession, AuthApiError } from './auth.js';

window.addEventListener('DOMContentLoaded', () => {
    if (getStoredEmail()) {
        window.location.href = 'index.html';
    }
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const emailInput = document.getElementById('emailInput');
    const passwordInput = document.getElementById('passwordInput');
    const errorMessage = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email) {
        showError('אנא הכנס אימייל');
        return;
    }
    if (!email.includes('@') || !email.includes('.')) {
        showError('אנא הכנס אימייל תקין');
        return;
    }
    if (!password) {
        showError('אנא הכנס סיסמה');
        return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = 'מתחבר...';
    errorMessage.classList.remove('show');

    try {
        const data = await loginUser({ email, password });
        saveUserSession(data.user);
        window.location.href = 'index.html';
    } catch (err) {
        showError(err instanceof AuthApiError ? err.message : 'שגיאה בהתחברות');
    }
});

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    loginBtn.disabled = false;
    loginBtn.textContent = 'התחבר';
}
