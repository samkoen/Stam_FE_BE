/**
 * Module de gestion de la page de login
 */
import {
    loginUser,
    getStoredEmail,
    saveUserSession,
    resendVerificationEmail,
    AuthApiError,
} from './auth.js';

window.addEventListener('DOMContentLoaded', () => {
    if (getStoredEmail()) {
        window.location.href = 'index.html';
        return;
    }
    const params = new URLSearchParams(window.location.search);
    const verified = params.get('verified');
    const verifyError = params.get('verify_error');
    if (verified === '1') {
        showSuccess('האימייל אומת בהצלחה! כעת ניתן להתחבר.');
    } else if (verified === 'already') {
        showSuccess('האימייל כבר אומת. ניתן להתחבר.');
    } else if (verifyError === 'invalid') {
        showError('קישור האימות לא תקין או שפג תוקפו');
    } else if (verifyError === 'notfound') {
        showError('משתמש לא נמצא');
    }
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const emailInput = document.getElementById('emailInput');
    const passwordInput = document.getElementById('passwordInput');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const resendWrap = document.getElementById('resendWrap');
    const loginBtn = document.getElementById('loginBtn');

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    successMessage.classList.remove('show');
    resendWrap.style.display = 'none';

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
        const msg = err instanceof AuthApiError ? err.message : 'שגיאה בהתחברות';
        showError(msg);
        if (err instanceof AuthApiError && err.status === 403 && msg.includes('לאמת')) {
            resendWrap.style.display = 'block';
            resendWrap.dataset.email = email;
        }
    }
});

document.getElementById('resendBtn')?.addEventListener('click', async () => {
    const wrap = document.getElementById('resendWrap');
    const btn = document.getElementById('resendBtn');
    const email = wrap?.dataset.email || document.getElementById('emailInput')?.value.trim();
    if (!email) return;
    btn.disabled = true;
    btn.textContent = 'שולח...';
    try {
        await resendVerificationEmail(email);
        showSuccess('נשלח אימייל אימות חדש. בדוק את תיבת הדואר.');
        wrap.style.display = 'none';
    } catch (err) {
        showError(err instanceof AuthApiError ? err.message : 'שגיאה בשליחה');
    } finally {
        btn.disabled = false;
        btn.textContent = 'שלח שוב אימייל אימות';
    }
});

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const loginBtn = document.getElementById('loginBtn');
    successMessage.classList.remove('show');
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    loginBtn.disabled = false;
    loginBtn.textContent = 'התחבר';
}

function showSuccess(message) {
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const loginBtn = document.getElementById('loginBtn');
    errorMessage.classList.remove('show');
    successMessage.textContent = message;
    successMessage.classList.add('show');
    loginBtn.disabled = false;
    loginBtn.textContent = 'התחבר';
}
