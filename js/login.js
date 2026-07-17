/**
 * Module de gestion de la page de login
 */
import {
    loginUser,
    getStoredEmail,
    saveUserSession,
    resendVerificationEmail,
    sendSupportMessage,
    AuthApiError,
} from './auth.js';
import { ApiService } from './api.js';

window.addEventListener('DOMContentLoaded', () => {
    if (getStoredEmail()) {
        window.location.href = 'index.html';
        return;
    }
    // Réveiller HF pendant saisie login / avant הרשמה
    ApiService.wakeUpServer().catch(() => {});
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

setupSupportModal();

function setupSupportModal() {
    const overlay = document.getElementById('supportOverlay');
    const openBtn = document.getElementById('openSupportBtn');
    const closeBtn = document.getElementById('closeSupportBtn');
    const sendBtn = document.getElementById('sendSupportBtn');
    const loginEmail = document.getElementById('emailInput');
    const supportEmail = document.getElementById('supportEmailInput');
    const supportPhone = document.getElementById('supportPhoneInput');
    const supportMessage = document.getElementById('supportMessageInput');
    const supportStatus = document.getElementById('supportStatus');

    if (!overlay || !openBtn) return;

    const openModal = () => {
        supportStatus.classList.remove('show', 'error', 'success');
        supportStatus.textContent = '';
        if (loginEmail?.value.trim() && supportEmail) {
            supportEmail.value = loginEmail.value.trim();
        }
        overlay.classList.add('show');
        overlay.setAttribute('aria-hidden', 'false');
        supportMessage?.focus();
    };

    const closeModal = () => {
        overlay.classList.remove('show');
        overlay.setAttribute('aria-hidden', 'true');
    };

    openBtn.addEventListener('click', openModal);
    closeBtn?.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    sendBtn?.addEventListener('click', async () => {
        const email = supportEmail?.value.trim() || '';
        const phone = supportPhone?.value.trim() || '';
        const message = supportMessage?.value.trim() || '';
        supportStatus.classList.remove('show', 'error', 'success');

        if (!email.includes('@')) {
            showSupportStatus('אנא הכנס אימייל תקין למענה', true);
            return;
        }
        if (message.length < 10) {
            showSupportStatus('ההודעה קצרה מדי (לפחות 10 תווים)', true);
            return;
        }

        sendBtn.disabled = true;
        sendBtn.textContent = 'שולח...';
        try {
            await sendSupportMessage({ email, message, phone });
            showSupportStatus('ההודעה נשלחה! נחזור אליך בהקדם.', false);
            if (supportMessage) supportMessage.value = '';
            setTimeout(closeModal, 2000);
        } catch (err) {
            showSupportStatus(
                err instanceof AuthApiError ? err.message : 'שגיאה בשליחה',
                true
            );
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = 'שלח';
        }
    });
}

function showSupportStatus(message, isError) {
    const el = document.getElementById('supportStatus');
    if (!el) return;
    el.textContent = message;
    el.className = `support-status show ${isError ? 'error' : 'success'}`;
}

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
