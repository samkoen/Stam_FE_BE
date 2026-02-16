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
        // Vérifier si l'utilisateur est connecté
        const userEmail = localStorage.getItem('stamstam_user_email');
        if (!userEmail) {
            // Rediriger vers la page de login si non connecté
            window.location.href = 'login.html';
            return;
        }
        
        this.ui = new UIManager();
        this.currentFile = null;
        this.currentImageBase64 = null;
        this.currentImageUrl = null;
        this.cropper = null;
        this.croppedFile = null;
        this.acceptedCroppedFile = null; // Image coupée acceptée par l'utilisateur
        this.userEmail = userEmail;
        this.init();
    }

    /**
     * Initialise l'application
     */
    init() {
        this.setupEventListeners();
        this.initializePanelSizes();
    }

    /**
     * Initialise les tailles des panneaux au démarrage
     */
    initializePanelSizes() {
        const leftPanel = this.ui.elements.leftPanel;
        const rightPanel = this.ui.elements.rightPanel;
        const resizer = this.ui.elements.panelResizer;
        
        if (!leftPanel || !rightPanel || !resizer) return;

        // Réinitialiser les styles pour utiliser les valeurs par défaut
        leftPanel.style.flex = '';
        leftPanel.style.flexBasis = '';
        rightPanel.style.flex = '';
        rightPanel.style.flexBasis = '';
    }

    /**
     * Configure les écouteurs d'événements
     */
    setupEventListeners() {
        // Nouveau bouton d'upload petit
        if (this.ui.elements.uploadBtnSmall) {
            this.ui.elements.uploadBtnSmall.addEventListener('click', () => {
                this.ui.elements.fileInput.click();
            });
        }

        // Upload area - clic (si existe encore)
        if (this.ui.elements.uploadArea) {
            this.ui.elements.uploadArea.addEventListener('click', () => {
                this.ui.elements.fileInput.click();
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
        }

        // File input - changement
        this.ui.elements.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Drag and drop sur le panneau d'image
        if (this.ui.elements.leftPanel) {
            this.ui.elements.leftPanel.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
            });

            this.ui.elements.leftPanel.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    this.handleFileSelect(e.dataTransfer.files[0]);
                }
            });
        }

        // Bouton de détection de lettres
        this.ui.elements.detectLettersBtn.addEventListener('click', () => {
            this.detectLetters();
        });

        // Bouton de réinitialisation
        this.ui.elements.resetBtn.addEventListener('click', () => {
            this.reset();
        });
        
        // Bouton de déconnexion
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
        
        // Afficher l'email de l'utilisateur
        const userEmailEl = document.getElementById('userEmail');
        if (userEmailEl) {
            userEmailEl.textContent = this.userEmail;
        }

        // Bouton de fermeture d'erreur
        this.ui.elements.errorCloseBtn.addEventListener('click', () => {
            this.ui.hideError();
        });

        // Bouton de téléchargement
        this.ui.elements.downloadBtn.addEventListener('click', () => {
            this.downloadResult();
        });

        // Bouton d'agrandissement (si existe)
        if (this.ui.elements.expandBtn) {
            this.ui.elements.expandBtn.addEventListener('click', () => {
                this.ui.toggleExpand();
            });
        }

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

        // Système de redimensionnement des panneaux
        this.setupPanelResizer();
    }

    /**
     * Configure le système de redimensionnement des panneaux
     */
    setupPanelResizer() {
        const resizer = this.ui.elements.panelResizer;
        const leftPanel = this.ui.elements.leftPanel;
        const rightPanel = this.ui.elements.rightPanel;
        
        if (!resizer || !leftPanel || !rightPanel) return;

        let isResizing = false;
        let startX = 0;
        let startY = 0;
        let startLeftPercent = 0;
        let isVertical = false;

        const checkLayout = () => {
            const container = leftPanel.parentElement;
            const computedStyle = window.getComputedStyle(container);
            isVertical = computedStyle.flexDirection === 'column';
        };

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            resizer.classList.add('resizing');
            startX = e.clientX;
            startY = e.clientY;
            checkLayout();
            
            const container = leftPanel.parentElement;
            if (isVertical) {
                const containerHeight = container.offsetHeight;
                const resizerHeight = resizer.offsetHeight;
                const availableHeight = containerHeight - resizerHeight;
                startLeftPercent = (leftPanel.offsetHeight / availableHeight) * 100;
                document.body.style.cursor = 'row-resize';
            } else {
                const containerWidth = container.offsetWidth;
                const resizerWidth = resizer.offsetWidth;
                const availableWidth = containerWidth - resizerWidth;
                startLeftPercent = (leftPanel.offsetWidth / availableWidth) * 100;
                document.body.style.cursor = 'col-resize';
            }
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const container = leftPanel.parentElement;
            let delta = 0;
            let containerSize = 0;
            const resizerSize = isVertical ? resizer.offsetHeight : resizer.offsetWidth;

            if (isVertical) {
                delta = e.clientY - startY;
                containerSize = container.offsetHeight;
            } else {
                delta = e.clientX - startX;
                containerSize = container.offsetWidth;
            }

            const availableSize = containerSize - resizerSize;

            // Calculer la nouvelle taille en pixels pour plus de précision
            // En RTL, inverser le delta pour que tirer vers la droite agrandisse le panneau de droite
            let newLeftSize = 0;
            
            if (isVertical) {
                const startLeftSize = (startLeftPercent / 100) * availableSize;
                newLeftSize = startLeftSize - delta;
            } else {
                const startLeftSize = (startLeftPercent / 100) * availableSize;
                newLeftSize = startLeftSize - delta;
            }

            // Limites minimales et maximales
            const minSize = 300;
            const maxSize = availableSize - minSize;

            if (newLeftSize < minSize) {
                newLeftSize = minSize;
            } else if (newLeftSize > maxSize) {
                newLeftSize = maxSize;
            }

            const newRightSize = availableSize - newLeftSize;

            // Appliquer les nouvelles tailles en pixels pour plus de précision
            // Utiliser flex-basis au lieu de width pour éviter les conflits
            leftPanel.style.flex = `0 0 ${newLeftSize}px`;
            leftPanel.style.flexBasis = `${newLeftSize}px`;
            rightPanel.style.flex = `0 0 ${newRightSize}px`;
            rightPanel.style.flexBasis = `${newRightSize}px`;
            
            // Forcer le recalcul du layout
            leftPanel.offsetHeight;
            rightPanel.offsetHeight;
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
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
        this.ui.setDetectLettersButtonEnabled(true);
        this.ui.elements.acceptCropBtn.style.display = 'none';
        this.ui.elements.cancelCropBtn.style.display = 'none';
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
            const result = await ApiService.detectLetters(fileToSend, this.userEmail);
            
            this.currentImageBase64 = result.image;
            // Log pour vérifier que le texte est bien reçu
            console.log('=== RÉSULTAT API ===');
            console.log('result:', result);
            console.log('result.text:', result.text);
            console.log('Type de result.text:', typeof result.text);
            console.log('Longueur de result.text:', result.text ? result.text.length : 0);
            
            // Afficher le résultat avec le nom de la paracha détectée, le texte et les différences
            this.ui.showResults(
                result.image,
                result.paracha,
                result.text || '',
                result.differences || [],
                result.parachaStatus || null,
                result.hasErrors,
                result.errors || null,
                result.confusableAccepted || []
            );
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
            
            // Accepter directement (plus d'étape intermédiaire)
            this.acceptCroppedImage();
            
        } catch (error) {
            this.ui.showError('שגיאה בחיתוך: ' + error.message);
        }
    }

    /**
     * Accepte l'image coupée et active les boutons de traitement
     */
    acceptCroppedImage() {
        if (!this.croppedFile) return;

        // Accepter l'image coupée
        this.acceptedCroppedFile = this.croppedFile;
        
        // Activer les boutons de traitement
        if (this.ui.elements.detectLettersBtn) {
            this.ui.elements.detectLettersBtn.disabled = false;
        }
        
        // Appeler aussi les fonctions de mise à jour
        this.ui.setDetectLettersButtonEnabled(true);
        
        // Masquer tous les boutons de crop
        this.ui.elements.applyCropBtn.style.display = 'none';
        this.ui.elements.acceptCropBtn.style.display = 'none';
        this.ui.elements.cancelCropBtn.style.display = 'none';
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
     * Déconnexion de l'utilisateur
     */
    logout() {
        localStorage.removeItem('stamstam_user_email');
        window.location.href = 'login.html';
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
