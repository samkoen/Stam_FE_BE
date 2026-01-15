/**
 * Module de gestion de l'interface utilisateur
 */
import { translateParachaName } from './config.js';

export class UIManager {
    constructor() {
        this.elements = {
            uploadSection: document.getElementById('uploadSection'),
            uploadArea: document.getElementById('uploadArea'),
            fileInput: document.getElementById('fileInput'),
            fileInfo: document.getElementById('fileInfo'),
            processBtn: document.getElementById('processBtn'),
            detectLettersBtn: document.getElementById('detectLettersBtn'),
            cropControls: document.getElementById('cropControls'),
            applyCropBtn: document.getElementById('applyCropBtn'),
            cancelCropBtn: document.getElementById('cancelCropBtn'),
            acceptCropBtn: document.getElementById('acceptCropBtn'),
            resetBtn: document.getElementById('resetBtn'),
            loadingSection: document.getElementById('loadingSection'),
            errorSection: document.getElementById('errorSection'),
            errorMessage: document.getElementById('errorMessage'),
            errorCloseBtn: document.getElementById('errorCloseBtn'),
            rightPanel: document.getElementById('rightPanel'),
            panelTitle: document.getElementById('panelTitle'),
            imageViewer: document.getElementById('imageViewer'),
            displayImage: document.getElementById('displayImage'),
            imagePlaceholder: document.querySelector('.image-placeholder'),
            imageInfo: document.getElementById('imageInfo'),
            parachaName: document.getElementById('parachaName'),
            legend: document.getElementById('legend'),
            expandBtn: document.getElementById('expandBtn'),
            cropBtn: document.getElementById('cropBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            imageZoomContainer: document.getElementById('imageZoomContainer'),
            zoomInBtn: document.getElementById('zoomInBtn'),
            zoomOutBtn: document.getElementById('zoomOutBtn'),
            resetZoomBtn: document.getElementById('resetZoomBtn')
        };
        this.isExpanded = false;
        this.zoomLevel = 1.0;
    }

    /**
     * Affiche les informations du fichier sélectionné
     * @param {File} file - Fichier sélectionné
     * @param {Function} formatFileSize - Fonction pour formater la taille
     */
    showFileInfo(file, formatFileSize) {
        const fileInfo = this.elements.fileInfo;
        fileInfo.innerHTML = `
            <div class="file-name">📄 ${file.name}</div>
            <div class="file-size">גודל: ${formatFileSize(file.size)}</div>
        `;
        fileInfo.classList.add('active');
    }

    /**
     * Affiche l'image sélectionnée dans le panneau de droite
     * @param {string} imageUrl - URL de l'image (object URL ou base64)
     */
    showSelectedImage(imageUrl) {
        this.elements.displayImage.src = imageUrl;
        this.elements.displayImage.style.display = 'block';
        this.elements.imageZoomContainer.style.display = 'block';
        this.elements.imagePlaceholder.style.display = 'none';
        this.elements.panelTitle.textContent = 'תמונה נבחרה';
        this.elements.imageInfo.style.display = 'none';
        this.elements.legend.style.display = 'none';
        this.elements.downloadBtn.style.display = 'none';
        this.elements.zoomInBtn.style.display = 'none';
        this.elements.zoomOutBtn.style.display = 'none';
        this.elements.resetZoomBtn.style.display = 'none';
        this.elements.cropBtn.style.display = 'inline-flex';
        this.elements.applyCropBtn.style.display = 'none';
        this.elements.acceptCropBtn.style.display = 'none';
        this.elements.cancelCropBtn.style.display = 'none';
        this.resetZoom();
    }

    /**
     * Affiche les résultats de l'analyse
     * @param {string} imageBase64 - Image en base64
     * @param {string} parachaName - Nom de la paracha détectée
     */
    showResults(imageBase64, parachaName) {
        this.elements.displayImage.src = `data:image/jpeg;base64,${imageBase64}`;
        this.elements.displayImage.style.display = 'block';
        this.elements.imageZoomContainer.style.display = 'block';
        this.elements.imagePlaceholder.style.display = 'none';
        this.elements.panelTitle.textContent = parachaName ? 'תוצאות הניתוח' : 'זיהוי אותיות';
        
        // Traduire le nom de la paracha en hébreu
        this.elements.parachaName.textContent = translateParachaName(parachaName);
        this.elements.imageInfo.style.display = parachaName ? 'block' : 'none';
        this.elements.legend.style.display = 'block';
        this.elements.downloadBtn.style.display = 'inline-flex';
        this.elements.zoomInBtn.style.display = 'inline-flex';
        this.elements.zoomOutBtn.style.display = 'inline-flex';
        this.elements.resetZoomBtn.style.display = 'inline-flex';
        this.elements.cropBtn.style.display = 'none';
        this.elements.applyCropBtn.style.display = 'none';
        this.elements.acceptCropBtn.style.display = 'none';
        this.elements.cancelCropBtn.style.display = 'none';
        this.resetZoom();
    }

    /**
     * Réinitialise l'affichage de l'image
     */
    resetImageDisplay() {
        this.elements.displayImage.style.display = 'none';
        this.elements.imageZoomContainer.style.display = 'none';
        this.elements.imagePlaceholder.style.display = 'block';
        this.elements.panelTitle.textContent = 'תצוגה מקדימה';
        this.elements.imageInfo.style.display = 'none';
        this.elements.legend.style.display = 'none';
        this.elements.downloadBtn.style.display = 'none';
        this.elements.zoomInBtn.style.display = 'none';
        this.elements.zoomOutBtn.style.display = 'none';
        this.elements.resetZoomBtn.style.display = 'none';
        this.elements.cropBtn.style.display = 'none';
        this.resetZoom();
    }

    /**
     * Zoom sur l'image
     * @param {number} delta - Delta de zoom (positif pour zoomer, négatif pour dézoomer)
     */
    zoomImage(delta) {
        this.zoomLevel = Math.max(0.5, Math.min(20.0, this.zoomLevel + delta));
        this.applyZoom();
    }

    /**
     * Réinitialise le zoom
     */
    resetZoom() {
        this.zoomLevel = 1.0;
        // Attendre que l'image soit chargée avant d'appliquer le zoom
        if (this.elements.displayImage.complete && this.elements.displayImage.naturalWidth > 0) {
            this.applyZoom();
        }
    }

    /**
     * Applique le zoom sur l'image
     */
    applyZoom() {
        if (this.elements.displayImage) {
            const img = this.elements.displayImage;
            // Calculer les dimensions naturelles
            if (img.naturalWidth && img.naturalHeight) {
                const container = this.elements.imageZoomContainer;
                const containerWidth = container.clientWidth || container.offsetWidth;
                const containerHeight = container.clientHeight || container.offsetHeight;
                
                // Calculer la taille de base pour que l'image rentre dans le conteneur au zoom 1.0
                const baseScale = Math.min(
                    containerWidth / img.naturalWidth,
                    containerHeight / img.naturalHeight,
                    1.0
                );
                
                // Appliquer le zoom: on peut maintenant zoomer au-delà de la taille du conteneur
                const scale = baseScale * this.zoomLevel;
                const newWidth = img.naturalWidth * scale;
                const newHeight = img.naturalHeight * scale;
                
                img.style.width = `${newWidth}px`;
                img.style.height = `${newHeight}px`;
                img.style.maxWidth = 'none';
                img.style.maxHeight = 'none';
                img.style.display = 'block';
            } else {
                // Si les dimensions naturelles ne sont pas encore disponibles, attendre le chargement
                // L'événement 'load' se chargera d'appliquer le zoom
            }
        }
    }

    /**
     * Active/désactive le bouton de traitement
     * @param {boolean} enabled - État du bouton
     */
    setProcessButtonEnabled(enabled) {
        if (this.elements.processBtn) {
            this.elements.processBtn.disabled = !enabled;
        }
    }

    /**
     * Active/désactive le bouton de détection de lettres
     * @param {boolean} enabled - État du bouton
     */
    setDetectLettersButtonEnabled(enabled) {
        if (this.elements.detectLettersBtn) {
            this.elements.detectLettersBtn.disabled = !enabled;
        }
    }

    /**
     * Affiche l'état de chargement
     * @param {boolean} show - Afficher ou masquer
     */
    showLoading(show) {
        if (show) {
            this.elements.loadingSection.classList.add('active');
            this.elements.processBtn.classList.add('loading');
            this.elements.processBtn.disabled = true;
        } else {
            this.elements.loadingSection.classList.remove('active');
            this.elements.processBtn.classList.remove('loading');
        }
    }

    /**
     * Affiche une erreur
     * @param {string} message - Message d'erreur
     */
    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorSection.classList.add('active');
    }

    /**
     * Masque l'erreur
     */
    hideError() {
        this.elements.errorSection.classList.remove('active');
    }

    /**
     * Ajoute la classe dragover à la zone d'upload
     * @param {boolean} add - Ajouter ou retirer la classe
     */
    setDragOver(add) {
        if (add) {
            this.elements.uploadArea.classList.add('dragover');
        } else {
            this.elements.uploadArea.classList.remove('dragover');
        }
    }

    /**
     * Bascule l'état d'agrandissement du panneau de droite
     */
    toggleExpand() {
        this.isExpanded = !this.isExpanded;
        if (this.isExpanded) {
            this.elements.rightPanel.classList.add('expanded');
            this.elements.expandBtn.textContent = '⛶';
            this.elements.expandBtn.title = 'Réduire';
        } else {
            this.elements.rightPanel.classList.remove('expanded');
            this.elements.expandBtn.textContent = '⛶';
            this.elements.expandBtn.title = 'Agrandir';
        }
    }

    /**
     * Réinitialise l'interface
     */
    reset() {
        this.elements.fileInfo.classList.remove('active');
        this.elements.fileInput.value = '';
        this.setProcessButtonEnabled(false);
        this.showLoading(false);
        this.hideError();
        this.resetImageDisplay();
        this.elements.resetBtn.style.display = 'none';
    }

    /**
     * Retourne l'image actuelle en base64
     * @returns {string|null} Image en base64 ou null
     */
    getCurrentImageBase64() {
        const src = this.elements.displayImage.src;
        if (src && src.startsWith('data:image')) {
            return src.split(',')[1];
        }
        return null;
    }
}
