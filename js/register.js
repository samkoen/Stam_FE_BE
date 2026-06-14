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

    errorMessage.classList.remove('show');

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
        showRegistrationSuccess(email);
    } catch (err) {
        showError(err instanceof AuthApiError ? err.message : 'שגיאה בהרשמה');
        registerBtn.disabled = false;
        registerBtn.textContent = 'הרשמה';
    }
});

function showRegistrationSuccess(email) {
    document.getElementById('registerForm').style.display = 'none';
    const authLink = document.getElementById('authLink');
    if (authLink) authLink.style.display = 'none';
    const subtitle = document.querySelector('.login-subtitle');
    if (subtitle) subtitle.textContent = 'אימות אימייל נדרש';
    document.getElementById('registeredEmailDisplay').textContent = email;
    document.getElementById('registerSuccessPanel').classList.add('show');
}

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}
