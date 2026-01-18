import { UIManager } from './ui.js';
import { FileHandler } from './fileHandler.js';
import { ApiService } from './api.js';
import { config } from './config.js';
import { ImageCropper } from './imageCropper.js';

/**
 * Application principale
 */
class App {
    constructor() {
        this.ui = new UIManager();
        this.currentFile = null;
        this.currentImageBase64 = null;
        this.currentImageUrl = null;
        this.cropper = null;
        this.croppedFile = null;
        this.acceptedCroppedFile = null; // Image coupée acceptée par l'utilisateur
        this.init();
    }

    /**
     * Initialise l'application
     */
    init() {
        this.setupEventListeners();
    }

    /**
     * Configure les écouteurs d'événements
     */
    setupEventListeners() {
        // Upload area - clic
        this.ui.elements.uploadArea.addEventListener('click', () => {
            this.ui.elements.fileInput.click();
        });

        // File input - changement
        this.ui.elements.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Drag and drop
        this.ui.elements.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.ui.setDragOver(true);
        });

        this.ui.elements.uploadArea.addEventListener('dragleave', () => {
            this.ui.setDragOver(false);
        });

        this.ui.elements.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.ui.setDragOver(false);
            this.handleFileSelect(e.dataTransfer.files[0]);
        });

        // Bouton de traitement
        this.ui.elements.processBtn.addEventListener('click', () => {
            this.processImage();
        });

        // Bouton de détection de lettres
        this.ui.elements.detectLettersBtn.addEventListener('click', () => {
            this.detectLetters();
        });

        // Bouton de réinitialisation
        this.ui.elements.resetBtn.addEventListener('click', () => {
            this.reset();
        });

        // Bouton de fermeture d'erreur
        this.ui.elements.errorCloseBtn.addEventListener('click', () => {
            this.ui.hideError();
        });

        // Bouton de téléchargement
        this.ui.elements.downloadBtn.addEventListener('click', () => {
            this.downloadResult();
        });

        // Bouton d'agrandissement
        this.ui.elements.expandBtn.addEventListener('click', () => {
            this.ui.toggleExpand();
        });

        // Bouton de crop
        this.ui.elements.cropBtn.addEventListener('click', () => {
            this.startCrop();
        });

        // Bouton pour appliquer le crop
        this.ui.elements.applyCropBtn.addEventListener('click', () => {
            this.applyCrop();
        });

        // Bouton pour annuler le crop
        this.ui.elements.cancelCropBtn.addEventListener('click', () => {
            this.cancelCrop();
        });

        // Bouton pour accepter l'image coupée
        this.ui.elements.acceptCropBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            console.log('Accept crop button clicked');
            this.acceptCroppedImage();
            return false;
        }, true); // Utiliser capture phase

        // Boutons de zoom
        this.ui.elements.zoomInBtn.addEventListener('click', () => {
            this.ui.zoomImage(0.2);
        });

        this.ui.elements.zoomOutBtn.addEventListener('click', () => {
            this.ui.zoomImage(-0.2);
        });

        this.ui.elements.resetZoomBtn.addEventListener('click', () => {
            this.ui.resetZoom();
        });

        // Zoom avec la molette de la souris
        this.ui.elements.imageZoomContainer.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            this.ui.zoomImage(delta);
        }, { passive: false });

        // Gestion du chargement de l'image pour appliquer le zoom
        this.ui.elements.displayImage.addEventListener('load', () => {
            this.ui.applyZoom();
        });
    }

    /**
     * Gère la sélection d'un fichier
     * @param {File} file - Fichier sélectionné
     */
    handleFileSelect(file) {
        if (!file) return;

        // Valider le fichier
        const validation = FileHandler.validateFile(file);
        if (!validation.valid) {
            this.ui.showError(validation.error);
            return;
        }

        // Libérer l'ancienne URL si elle existe
        if (this.currentImageUrl) {
            FileHandler.revokeImagePreview(this.currentImageUrl);
        }

        this.currentFile = file;
        this.ui.hideError();
        
        // Afficher l'image sélectionnée dans le panneau de droite
        this.currentImageUrl = FileHandler.createImagePreview(file);
        this.ui.showSelectedImage(this.currentImageUrl);
        this.ui.elements.resetBtn.style.display = 'inline-flex';
        
        // Réinitialiser le crop
        this.croppedFile = null;
        this.acceptedCroppedFile = null;
        if (this.cropper) {
            this.cropper.remove();
            this.cropper = null;
        }
        // Activer les boutons de traitement
        this.ui.setProcessButtonEnabled(true);
        this.ui.setDetectLettersButtonEnabled(true);
        this.ui.elements.acceptCropBtn.style.display = 'none';
        this.ui.elements.cancelCropBtn.style.display = 'none';
    }

    /**
     * Traite l'image
     */
    async processImage() {
        if (!this.currentFile) return;

        try {
            this.ui.showLoading(true);
            this.ui.hideError();

            // Utiliser l'image coupée acceptée si disponible, sinon l'originale
            const fileToSend = this.acceptedCroppedFile || this.currentFile;
            const result = await ApiService.processImage(fileToSend);
            
            this.currentImageBase64 = result.image;
            this.ui.showResults(result.image, result.paracha);
        } catch (error) {
            this.ui.showError(error.message || config.MESSAGES.ERROR_PROCESS);
        } finally {
            this.ui.showLoading(false);
        }
    }

    /**
     * Détecte les lettres dans l'image
     */
    async detectLetters() {
        if (!this.currentFile) return;

        try {
            this.ui.showLoading(true);
            this.ui.hideError();

            // Utiliser l'image coupée acceptée si disponible, sinon l'originale
            const fileToSend = this.acceptedCroppedFile || this.currentFile;
            const result = await ApiService.detectLetters(fileToSend);
            
            this.currentImageBase64 = result.image;
            // Log pour vérifier que le texte est bien reçu
            console.log('=== RÉSULTAT API ===');
            console.log('result:', result);
            console.log('result.text:', result.text);
            console.log('Type de result.text:', typeof result.text);
            console.log('Longueur de result.text:', result.text ? result.text.length : 0);
            
            // Afficher le résultat avec le nom de la paracha détectée, le texte et les différences
            this.ui.showResults(result.image, result.paracha, result.text || '', result.differences || []);
            this.ui.elements.panelTitle.textContent = 'זיהוי אותיות';
        } catch (error) {
            this.ui.showError(error.message || 'שגיאה בזיהוי האותיות');
        } finally {
            this.ui.showLoading(false);
        }
    }

    /**
     * Démarre le mode crop
     */
    startCrop() {
        if (!this.ui.elements.displayImage || !this.ui.elements.imageZoomContainer) {
            return;
        }

        if (!this.cropper) {
            this.cropper = new ImageCropper(
                this.ui.elements.displayImage,
                this.ui.elements.imageZoomContainer
            );
        }

        if (this.cropper.start()) {
            // Afficher les contrôles de crop
            this.ui.elements.cropControls.style.display = 'block';
            // Afficher les boutons de crop à côté du bouton crop
            this.ui.elements.applyCropBtn.style.display = 'inline-flex';
            this.ui.elements.acceptCropBtn.style.display = 'none';
            this.ui.elements.cancelCropBtn.style.display = 'inline-flex';
            // Désactiver les boutons de traitement pendant le crop
            this.ui.setProcessButtonEnabled(false);
            this.ui.setDetectLettersButtonEnabled(false);
        }
    }

    /**
     * Annule le crop
     */
    cancelCrop() {
        if (this.cropper) {
            this.cropper.stop();
        }
        this.ui.elements.cropControls.style.display = 'none';
        // Masquer tous les boutons de crop
        this.ui.elements.applyCropBtn.style.display = 'none';
        this.ui.elements.acceptCropBtn.style.display = 'none';
        this.ui.elements.cancelCropBtn.style.display = 'none';
        
        // Si on annule après avoir appliqué le crop (mais pas accepté), restaurer l'image originale
        if (this.croppedFile && !this.acceptedCroppedFile) {
            // Restaurer l'image originale
            if (this.currentImageUrl && this.currentImageUrl.startsWith('blob:')) {
                URL.revokeObjectURL(this.currentImageUrl);
            }
            this.currentImageUrl = FileHandler.createImagePreview(this.currentFile);
            this.ui.showSelectedImage(this.currentImageUrl);
            this.croppedFile = null;
        }
        
        // Réactiver les boutons (utiliser l'image acceptée si disponible, sinon l'originale)
        this.ui.setProcessButtonEnabled(true);
        this.ui.setDetectLettersButtonEnabled(true);
    }

    /**
     * Applique le crop
     */
    async applyCrop() {
        if (!this.cropper) return;

        try {
            const croppedBlob = await this.cropper.apply();
            if (!croppedBlob) {
                this.ui.showError('אנא בחר אזור תקין');
                return;
            }

            // Créer un nouveau fichier à partir du blob
            this.croppedFile = new File([croppedBlob], this.currentFile.name, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });

            // Afficher l'image coupée
            const croppedUrl = URL.createObjectURL(croppedBlob);
            if (this.currentImageUrl && this.currentImageUrl.startsWith('blob:')) {
                URL.revokeObjectURL(this.currentImageUrl);
            }
            this.currentImageUrl = croppedUrl;
            this.ui.showSelectedImage(croppedUrl);

            // Arrêter le mode crop
            this.cropper.stop();
            this.ui.elements.cropControls.style.display = 'none';
            
            // Masquer le bouton d'application, afficher le bouton d'acceptation et d'annulation
            this.ui.elements.applyCropBtn.style.display = 'none';
            this.ui.elements.acceptCropBtn.style.display = 'inline-flex';
            this.ui.elements.cancelCropBtn.style.display = 'inline-flex';
            // Désactiver les boutons de traitement jusqu'à ce que l'utilisateur accepte l'image
            this.ui.setProcessButtonEnabled(false);
            this.ui.setDetectLettersButtonEnabled(false);
        } catch (error) {
            this.ui.showError('שגיאה בחיתוך: ' + error.message);
        }
    }

    /**
     * Accepte l'image coupée et active les boutons de traitement
     */
    acceptCroppedImage() {
        console.log('acceptCroppedImage called, croppedFile:', this.croppedFile);
        if (!this.croppedFile) {
            console.warn('Aucune image coupée à accepter');
            return;
        }

        // Accepter l'image coupée
        this.acceptedCroppedFile = this.croppedFile;
        console.log('Image acceptée, acceptedCroppedFile:', this.acceptedCroppedFile);
        
        // Activer les boutons de traitement AVANT de masquer les boutons de crop
        // pour éviter tout problème de timing
        if (this.ui.elements.detectLettersBtn) {
            this.ui.elements.detectLettersBtn.disabled = false;
            console.log('detectLettersBtn disabled set to false');
        }
        if (this.ui.elements.processBtn) {
            this.ui.elements.processBtn.disabled = false;
            console.log('processBtn disabled set to false');
        }
        
        // Appeler aussi les fonctions de mise à jour
        this.ui.setProcessButtonEnabled(true);
        this.ui.setDetectLettersButtonEnabled(true);
        
        // Masquer tous les boutons de crop après avoir activé les boutons
        this.ui.elements.applyCropBtn.style.display = 'none';
        this.ui.elements.acceptCropBtn.style.display = 'none';
        this.ui.elements.cancelCropBtn.style.display = 'none';
        
        // Forcer un reflow pour s'assurer que les changements sont appliqués
        void this.ui.elements.detectLettersBtn.offsetHeight;
    }

    /**
     * Télécharge le résultat
     */
    downloadResult() {
        const imageBase64 = this.ui.getCurrentImageBase64();
        if (imageBase64) {
            const filename = this.currentFile 
                ? `resultat_${this.currentFile.name.replace(/\.[^/.]+$/, '')}.jpg`
                : 'resultat.jpg';
            FileHandler.downloadImage(imageBase64, filename);
        }
    }

    /**
     * Réinitialise l'application
     */
    reset() {
        // Libérer l'URL de l'image
        if (this.currentImageUrl) {
            FileHandler.revokeImagePreview(this.currentImageUrl);
            this.currentImageUrl = null;
        }
        
        if (this.cropper) {
            this.cropper.remove();
            this.cropper = null;
        }
        
        this.currentFile = null;
        this.currentImageBase64 = null;
        this.croppedFile = null;
        this.acceptedCroppedFile = null;
        this.ui.reset();
        if (this.ui.elements.cropControls) {
            this.ui.elements.cropControls.style.display = 'none';
        }
        if (this.ui.elements.applyCropBtn) {
            this.ui.elements.applyCropBtn.style.display = 'none';
        }
        if (this.ui.elements.acceptCropBtn) {
            this.ui.elements.acceptCropBtn.style.display = 'none';
        }
        if (this.ui.elements.cancelCropBtn) {
            this.ui.elements.cancelCropBtn.style.display = 'none';
        }
    }
}

// Initialiser l'application quand le DOM est prêt
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new App();
    });
} else {
    new App();
}
