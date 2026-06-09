/**
 * Page d'inscription
 */
import { registerUser, getStoredEmail, AuthApiError } from './auth.js';

window.addEventListener('DOMContentLoaded', () => {
    if (getStoredEmail()) {
        window.location.href = 'index.html';
    }
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const fullName = document.getElementById('fullNameInput').value.trim();
    const email = document.getElementById('emailInput').value.trim();
    const password = document.getElementById('passwordInput').value;
    const phone = document.getElementById('phoneInput').value.trim();
    const registerBtn = document.getElementById('registerBtn');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');

    errorMessage.classList.remove('show');
    successMessage.classList.remove('show');

    if (!fullName || fullName.length < 2) {
        showError('אנא הכנס שם מלא');
        return;
    }
    if (!email.includes('@')) {
        showError('אנא הכנס אימייל תקין');
        return;
    }
    if (password.length < 6) {
        showError('הסיסמה חייבת להכיל לפחות 6 תווים');
        return;
    }

    registerBtn.disabled = true;
    registerBtn.textContent = 'נרשם...';

    try {
        await registerUser({ email, password, full_name: fullName, phone });
        document.getElementById('registerForm').style.display = 'none';
        successMessage.textContent = 'נרשמת בהצלחה! נשלח אליך אימייל לאימות. לאחר האימות תוכל להתחבר.';
        successMessage.classList.add('show');
    } catch (err) {
        showError(err instanceof AuthApiError ? err.message : 'שגיאה בהרשמה');
    } finally {
        registerBtn.disabled = false;
        registerBtn.textContent = 'הרשמה';
    }
});

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}
