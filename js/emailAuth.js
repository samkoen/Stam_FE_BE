/**
 * Module d'authentification par email (envoi et vérification du code).
 * Gère le flux : saisie email → envoi code → saisie code → accès app.
 */
import { ApiService } from './api.js';

const STEP_EMAIL = 1;
const STEP_CODE = 2;

/**
 * Initialise le flux de login par email sur la page.
 * @param {Object} elements - { form, emailInput, codeGroup, codeInput, submitBtn, backBtn, errorEl }
 * @param {Object} callbacks - { onSuccess: () => void }
 */
export function initEmailAuthLogin(elements, callbacks = {}) {
    const {
        form,
        emailInput,
        codeGroup,
        codeInput,
        submitBtn,
        backBtn,
        errorEl
    } = elements;

    let step = STEP_EMAIL;
    let currentEmail = '';

    function showError(msg) {
        if (errorEl) {
            errorEl.textContent = msg || '';
            errorEl.classList.toggle('show', !!msg);
        }
    }

    function setStep(s) {
        step = s;
        if (step === STEP_EMAIL) {
            if (codeGroup) codeGroup.style.display = 'none';
            if (submitBtn) submitBtn.textContent = 'התחבר';
            if (backBtn) backBtn.style.display = 'none';
        } else {
            if (codeGroup) codeGroup.style.display = 'block';
            if (submitBtn) submitBtn.textContent = 'אישור';
            if (backBtn) backBtn.style.display = 'block';
            if (codeInput) {
                codeInput.value = '';
                codeInput.focus();
            }
        }
        showError('');
    }

    function setLoading(loading) {
        if (submitBtn) {
            submitBtn.disabled = loading;
            submitBtn.textContent = loading ? '...' : (step === STEP_EMAIL ? 'התחבר' : 'אישור');
        }
    }

    async function handleSubmit(e) {
        e.preventDefault();
        showError('');
        if (step === STEP_EMAIL) {
            const email = (emailInput?.value || '').trim();
            if (!email || !email.includes('@') || !email.includes('.')) {
                showError('אנא הכנס אימייל תקין');
                return;
            }
            currentEmail = email;
            setLoading(true);
            try {
                const res = await ApiService.requestLogin(email);
                if (res.requiresCode === false && res.email) {
                    localStorage.setItem('stamstam_user_email', res.email);
                    if (callbacks.onSuccess) callbacks.onSuccess();
                    else window.location.href = 'index.html';
                    return;
                }
                setStep(STEP_CODE);
            } catch (err) {
                showError(err.message || 'שגיאה בהתחברות');
            } finally {
                setLoading(false);
            }
        } else {
            const code = (codeInput?.value || '').trim();
            if (!code) {
                showError('אנא הכנס את הקוד');
                return;
            }
            setLoading(true);
            try {
                const res = await ApiService.verifyAuthCode(currentEmail, code);
                if (res.email) {
                    localStorage.setItem('stamstam_user_email', res.email);
                    if (callbacks.onSuccess) callbacks.onSuccess();
                    else window.location.href = 'index.html';
                }
            } catch (err) {
                showError(err.message || 'קוד לא תקין או שפג תוקף');
            } finally {
                setLoading(false);
            }
        }
    }

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            setStep(STEP_EMAIL);
        });
    }

    if (form) {
        form.addEventListener('submit', handleSubmit);
    }

    setStep(STEP_EMAIL);
}
