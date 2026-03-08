/**
 * Module layout résultats pour l'app uniquement (Capacitor).
 * Écran séparé en 2 : image en haut (zoom etc.), liste d'erreurs en bas (scroll indépendant).
 * Au clic sur une erreur, l'image zoome dessus sans faire défiler la page.
 */
import { Capacitor } from '@capacitor/core';

const MAIN_LAYOUT_ID = 'mainLayout';
const CLASS_APP_RESULTS = 'layout-app-results';
const BODY_CLASS = 'layout-app-results-active';

/**
 * Indique si on tourne dans l'app native (Capacitor), pas dans le navigateur.
 * @returns {boolean}
 */
export function isApp() {
    return Capacitor.getPlatform() !== 'web';
}

/**
 * Active le layout "app résultats" : partie haute = image fixe, partie basse = erreurs (scroll seule).
 * Bloque le scroll de la page pour que seul le panneau du bas défile.
 */
export function enterAppResultsLayout() {
    const el = document.getElementById(MAIN_LAYOUT_ID);
    if (el) el.classList.add(CLASS_APP_RESULTS);
    document.body.classList.add(BODY_CLASS);
    const container = document.querySelector('.app-container');
    if (container) container.classList.add(BODY_CLASS);
    const appResetBtn = document.getElementById('appResetBtn');
    if (appResetBtn) appResetBtn.style.display = '';
}

/**
 * Désactive le layout "app résultats".
 */
export function exitAppResultsLayout() {
    const el = document.getElementById(MAIN_LAYOUT_ID);
    if (el) el.classList.remove(CLASS_APP_RESULTS);
    document.body.classList.remove(BODY_CLASS);
    const container = document.querySelector('.app-container');
    if (container) container.classList.remove(BODY_CLASS);
    const appResetBtn = document.getElementById('appResetBtn');
    if (appResetBtn) appResetBtn.style.display = 'none';
    const left = document.getElementById('leftImagePanel');
    const right = document.getElementById('rightResultsPanel');
    if (left) { left.style.flex = ''; left.style.flexBasis = ''; }
    if (right) { right.style.flex = ''; right.style.flexBasis = ''; }
}

export { CLASS_APP_RESULTS };
