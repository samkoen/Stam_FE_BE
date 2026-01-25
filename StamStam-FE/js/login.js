/**
 * Module de gestion de la page de login
 */

// Vérifier si l'utilisateur est déjà connecté
window.addEventListener('DOMContentLoaded', () => {
    const userEmail = localStorage.getItem('stamstam_user_email');
    if (userEmail) {
        // Rediriger vers la page principale si déjà connecté
        window.location.href = 'index.html';
    }
});

// Gestion du formulaire de login
document.getElementById('loginForm').addEventListener('submit', (e) => {
    e.preventDefault();
    
    const emailInput = document.getElementById('emailInput');
    const errorMessage = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');
    
    const email = emailInput.value.trim();
    
    // Valider l'email
    if (!email) {
        showError('אנא הכנס אימייל');
        return;
    }
    
    if (!email.includes('@') || !email.includes('.')) {
        showError('אנא הכנס אימייל תקין');
        return;
    }
    
    // Désactiver le bouton pendant le traitement
    loginBtn.disabled = true;
    loginBtn.textContent = 'מתחבר...';
    errorMessage.classList.remove('show');
    
    // Simuler une validation (pour l'instant, on accepte n'importe quel email valide)
    // Plus tard, on pourra ajouter une vérification côté serveur
    setTimeout(() => {
        // Sauvegarder l'email dans localStorage
        localStorage.setItem('stamstam_user_email', email);
        
        // Rediriger vers la page principale
        window.location.href = 'index.html';
    }, 300);
});

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    
    // Réactiver le bouton
    const loginBtn = document.getElementById('loginBtn');
    loginBtn.disabled = false;
    loginBtn.textContent = 'התחבר';
}

