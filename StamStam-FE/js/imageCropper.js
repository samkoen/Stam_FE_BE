/**
 * Module pour le recadrage d'image avec rectangle de sélection redimensionnable
 */
export class ImageCropper {
    constructor(imageElement, containerElement) {
        this.imageElement = imageElement;
        this.containerElement = containerElement;
        this.isActive = false;
        this.cropOverlay = null;
        this.cropBox = null;
        this.handles = [];
        
        // Position et taille du rectangle de crop
        this.cropX = 0;
        this.cropY = 0;
        this.cropWidth = 0;
        this.cropHeight = 0;
        
        // État de l'interaction
        this.isDragging = false;
        this.isResizing = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.resizeHandle = null;
        
        // Dimensions de l'image
        this.imageRect = null;
    }

    /**
     * Crée l'overlay et le rectangle de sélection
     */
    createElements() {
        // Vérifier si l'overlay existe déjà
        const existing = this.containerElement.querySelector('.crop-overlay');
        if (existing) {
            this.cropOverlay = existing;
            this.cropBox = existing.querySelector('.crop-box');
            this.handles = Array.from(existing.querySelectorAll('.crop-handle'));
            return;
        }

        // Créer l'overlay
        this.cropOverlay = document.createElement('div');
        this.cropOverlay.className = 'crop-overlay';
        this.cropOverlay.style.display = 'none';
        this.containerElement.appendChild(this.cropOverlay);

        // Créer la boîte de sélection
        this.cropBox = document.createElement('div');
        this.cropBox.className = 'crop-box';
        this.cropOverlay.appendChild(this.cropBox);

        // Créer les poignées (handles) aux 4 coins
        const handlePositions = ['nw', 'ne', 'sw', 'se']; // nord-ouest, nord-est, sud-ouest, sud-est
        handlePositions.forEach(pos => {
            const handle = document.createElement('div');
            handle.className = `crop-handle crop-handle-${pos}`;
            handle.dataset.position = pos;
            this.cropBox.appendChild(handle);
            this.handles.push(handle);
        });

        // Event listeners pour le déplacement du rectangle
        this.cropBox.addEventListener('mousedown', this.onBoxMouseDown = this.handleBoxMouseDown.bind(this));
        
        // Event listeners pour le redimensionnement via les poignées
        this.handles.forEach(handle => {
            handle.addEventListener('mousedown', this.onHandleMouseDown = this.handleHandleMouseDown.bind(this));
        });
    }

    /**
     * Démarre le mode crop
     */
    start() {
        if (!this.imageElement.complete || this.imageElement.naturalWidth === 0) {
            console.error('Image not loaded');
            return false;
        }

        this.createElements();
        this.updateImageRect();
        
        // Initialiser le rectangle de crop au centre de l'image (80% de la taille)
        const margin = 0.1;
        this.cropX = this.imageRect.width * margin;
        this.cropY = this.imageRect.height * margin;
        this.cropWidth = this.imageRect.width * (1 - 2 * margin);
        this.cropHeight = this.imageRect.height * (1 - 2 * margin);
        
        this.isActive = true;
        this.cropOverlay.style.display = 'block';
        this.imageElement.style.cursor = 'default';
        
        this.updateCropBox();
        
        // Event listeners globaux pour le drag
        document.addEventListener('mousemove', this.onMouseMove = this.handleMouseMove.bind(this));
        document.addEventListener('mouseup', this.onMouseUp = this.handleMouseUp.bind(this));
        
        return true;
    }

    /**
     * Arrête le mode crop
     */
    stop() {
        this.isActive = false;
        if (this.cropOverlay) {
            this.cropOverlay.style.display = 'none';
        }
        if (this.imageElement) {
            this.imageElement.style.cursor = 'default';
        }
        
        // Retirer les event listeners globaux
        if (this.onMouseMove) {
            document.removeEventListener('mousemove', this.onMouseMove);
        }
        if (this.onMouseUp) {
            document.removeEventListener('mouseup', this.onMouseUp);
        }
    }

    /**
     * Met à jour les dimensions de l'image
     */
    updateImageRect() {
        const imageRect = this.imageElement.getBoundingClientRect();
        const containerRect = this.containerElement.getBoundingClientRect();
        const scrollLeft = this.containerElement.scrollLeft;
        const scrollTop = this.containerElement.scrollTop;
        
        // Calculer la position de l'image relative au conteneur (en tenant compte du centrage)
        this.imageRect = {
            left: imageRect.left - containerRect.left + scrollLeft,
            top: imageRect.top - containerRect.top + scrollTop,
            width: imageRect.width,
            height: imageRect.height
        };
    }
    
    /**
     * Convertit les coordonnées de la souris en coordonnées relatives à l'image
     */
    getImageCoordinates(clientX, clientY) {
        const imageRect = this.imageElement.getBoundingClientRect();
        return {
            x: clientX - imageRect.left,
            y: clientY - imageRect.top
        };
    }

    /**
     * Met à jour la position et la taille de la boîte de crop
     */
    updateCropBox() {
        if (!this.cropBox || !this.imageRect) return;

        // Limiter aux dimensions de l'image
        this.cropX = Math.max(0, Math.min(this.cropX, this.imageRect.width - this.cropWidth));
        this.cropY = Math.max(0, Math.min(this.cropY, this.imageRect.height - this.cropHeight));
        this.cropWidth = Math.max(50, Math.min(this.cropWidth, this.imageRect.width - this.cropX));
        this.cropHeight = Math.max(50, Math.min(this.cropHeight, this.imageRect.height - this.cropY));

        // Positionner le rectangle par rapport à l'image (qui peut être centrée dans le conteneur)
        this.cropBox.style.left = `${this.imageRect.left + this.cropX}px`;
        this.cropBox.style.top = `${this.imageRect.top + this.cropY}px`;
        this.cropBox.style.width = `${this.cropWidth}px`;
        this.cropBox.style.height = `${this.cropHeight}px`;
    }

    /**
     * Gère le début du déplacement du rectangle
     */
    handleBoxMouseDown(e) {
        if (e.target.classList.contains('crop-handle')) {
            return; // Laisser les handles gérer leur propre drag
        }
        
        this.isDragging = true;
        this.updateImageRect();
        
        // Convertir les coordonnées de la souris en coordonnées relatives à l'image
        const coords = this.getImageCoordinates(e.clientX, e.clientY);
        this.dragStartX = coords.x;
        this.dragStartY = coords.y;
        
        // Stocker la position initiale du rectangle
        this.dragStartCropX = this.cropX;
        this.dragStartCropY = this.cropY;
        
        this.cropBox.style.cursor = 'move';
        e.preventDefault();
    }

    /**
     * Gère le début du redimensionnement via une poignée
     */
    handleHandleMouseDown(e) {
        this.isResizing = true;
        this.resizeHandle = e.target.dataset.position;
        this.updateImageRect();
        
        // Convertir les coordonnées de la souris en coordonnées relatives à l'image
        const coords = this.getImageCoordinates(e.clientX, e.clientY);
        this.dragStartX = coords.x;
        this.dragStartY = coords.y;
        
        // Stocker la position et taille initiales du rectangle
        this.dragStartCropX = this.cropX;
        this.dragStartCropY = this.cropY;
        this.dragStartCropWidth = this.cropWidth;
        this.dragStartCropHeight = this.cropHeight;
        
        e.preventDefault();
        e.stopPropagation();
    }

    /**
     * Gère le mouvement de la souris
     */
    handleMouseMove(e) {
        if (!this.isActive) return;
        
        this.updateImageRect();
        
        // Convertir les coordonnées de la souris en coordonnées relatives à l'image
        const coords = this.getImageCoordinates(e.clientX, e.clientY);
        const currentX = coords.x;
        const currentY = coords.y;
        
        if (this.isDragging) {
            // Déplacer le rectangle
            const deltaX = currentX - this.dragStartX;
            const deltaY = currentY - this.dragStartY;
            
            this.cropX = this.dragStartCropX + deltaX;
            this.cropY = this.dragStartCropY + deltaY;
            
            this.updateCropBox();
        } else if (this.isResizing && this.resizeHandle) {
            // Redimensionner le rectangle
            const deltaX = currentX - this.dragStartX;
            const deltaY = currentY - this.dragStartY;
            
            const handle = this.resizeHandle;
            
            if (handle.includes('n')) { // Nord (haut)
                this.cropY = this.dragStartCropY + deltaY;
                this.cropHeight = this.dragStartCropHeight - deltaY;
            }
            if (handle.includes('s')) { // Sud (bas)
                this.cropHeight = this.dragStartCropHeight + deltaY;
            }
            if (handle.includes('w')) { // Ouest (gauche)
                this.cropX = this.dragStartCropX + deltaX;
                this.cropWidth = this.dragStartCropWidth - deltaX;
            }
            if (handle.includes('e')) { // Est (droite)
                this.cropWidth = this.dragStartCropWidth + deltaX;
            }
            
            this.updateCropBox();
        }
    }

    /**
     * Gère la fin de l'interaction
     */
    handleMouseUp(e) {
        if (this.isDragging) {
            this.isDragging = false;
            if (this.cropBox) {
                this.cropBox.style.cursor = 'default';
            }
        }
        if (this.isResizing) {
            this.isResizing = false;
            this.resizeHandle = null;
        }
    }

    /**
     * Applique le crop et retourne le blob de l'image coupée
     */
    async apply() {
        if (!this.isActive || this.cropWidth <= 0 || this.cropHeight <= 0) {
            return null;
        }

        // Calculer les coordonnées réelles dans l'image originale
        const scaleX = this.imageElement.naturalWidth / this.imageRect.width;
        const scaleY = this.imageElement.naturalHeight / this.imageRect.height;

        const x = this.cropX * scaleX;
        const y = this.cropY * scaleY;
        const width = this.cropWidth * scaleX;
        const height = this.cropHeight * scaleY;

        if (width <= 0 || height <= 0) {
            return null;
        }

        // Créer un canvas pour le crop
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // Dessiner la partie coupée
        ctx.drawImage(
            this.imageElement,
            x, y, width, height,
            0, 0, width, height
        );

        // Convertir en blob
        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                resolve(blob);
            }, 'image/jpeg', 1.0);
        });
    }

    /**
     * Supprime l'overlay
     */
    remove() {
        if (this.cropOverlay && this.cropOverlay.parentNode) {
            this.cropOverlay.parentNode.removeChild(this.cropOverlay);
        }
        this.cropOverlay = null;
        this.cropBox = null;
        this.handles = [];
    }
}

