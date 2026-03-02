/**
 * Module de gestion de la page de login (authentification par code email).
 */
import { initEmailAuthLogin } from './emailAuth.js';

window.addEventListener('DOMContentLoaded', () => {
    const userEmail = localStorage.getItem('stamstam_user_email');
    if (userEmail) {
        window.location.href = 'index.html';
        return;
    }

    initEmailAuthLogin(
        {
            form: document.getElementById('loginForm'),
            emailInput: document.getElementById('emailInput'),
            codeGroup: document.getElementById('codeGroup'),
            codeInput: document.getElementById('codeInput'),
            submitBtn: document.getElementById('loginBtn'),
            backBtn: document.getElementById('backBtn'),
            errorEl: document.getElementById('errorMessage')
        },
        { onSuccess: () => { window.location.href = 'index.html'; } }
    );
});
