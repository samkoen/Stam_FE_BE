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
            detectedText: document.getElementById('detectedText'),
            legend: document.getElementById('legend'),
            expandBtn: document.getElementById('expandBtn'),
            cropBtn: document.getElementById('cropBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            imageZoomContainer: document.getElementById('imageZoomContainer'),
            zoomInBtn: document.getElementById('zoomInBtn'),
            zoomOutBtn: document.getElementById('zoomOutBtn'),
            resetZoomBtn: document.getElementById('resetZoomBtn'),
            differencesInfo: document.getElementById('differencesInfo')
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
     * @param {string} detectedText - Texte hébreu détecté
     * @param {Array} differences - Liste des différences trouvées
     */
    showResults(imageBase64, parachaName, detectedText = '', differences = [], parachaStatus = null, hasErrors = null, errors = null) {
        this.elements.displayImage.src = `data:image/jpeg;base64,${imageBase64}`;
        this.elements.displayImage.style.display = 'block';
        this.elements.imageZoomContainer.style.display = 'block';
        this.elements.imagePlaceholder.style.display = 'none';
        this.elements.panelTitle.textContent = parachaName ? 'תוצאות הניתוח' : 'זיהוי אותיות';
        
        // Traduire le nom de la paracha en hébreu
        this.elements.parachaName.textContent = translateParachaName(parachaName);
        
        // Statut global (complete / incomplete) et erreurs
        const parachaStatusEl = document.getElementById('parachaStatus');
        const errorsStatusEl = document.getElementById('errorsStatus');
        if (parachaStatusEl) {
            if (parachaStatus === 'complete') {
                parachaStatusEl.textContent = 'פרשה מלאה';
                parachaStatusEl.className = 'info-value status-pill status-success';
            } else if (parachaStatus === 'incomplete') {
                parachaStatusEl.textContent = 'פרשה חלקית';
                parachaStatusEl.className = 'info-value status-pill status-warning';
            } else {
                parachaStatusEl.textContent = '';
                parachaStatusEl.className = 'info-value status-pill';
            }
        }
        if (errorsStatusEl) {
            if (hasErrors === false) {
                errorsStatusEl.textContent = 'ללא שגיאות';
                errorsStatusEl.className = 'info-value status-pill status-success';
            } else if (errors) {
                const missing = errors.missing || 0;
                const extra = errors.extra || 0;
                const wrong = errors.wrong || 0;
                const total = missing + extra + wrong;
                errorsStatusEl.textContent = `שגיאות: ${total} (חסר ${missing}, מיותר ${extra}, שגוי ${wrong})`;
                errorsStatusEl.className = 'info-value status-pill status-error';
            } else {
                errorsStatusEl.textContent = '';
                errorsStatusEl.className = 'info-value status-pill';
            }
        }
        
        // Afficher le message de succès en haut si pas de différences
        const successMessageEl = document.getElementById('successMessage');
        if (successMessageEl) {
            if (!differences || differences.length === 0) {
                successMessageEl.innerHTML = '<span class="success-message">✅ התוצאה מושלמת! 100% התאמה</span>';
                successMessageEl.style.display = 'block';
            } else {
                successMessageEl.style.display = 'none';
            }
        }
        
        // Afficher le texte détecté - toujours afficher l'élément
        const detectedTextItem = document.getElementById('detectedTextItem');
        const detectedTextEl = document.getElementById('detectedText');
        
        // Log pour déboguer AVANT le traitement
        console.log('=== DÉBOGAGE TEXTE (AVANT) ===');
        console.log('detectedText param:', detectedText);
        console.log('Type detectedText:', typeof detectedText);
        console.log('detectedTextEl:', detectedTextEl);
        console.log('detectedTextItem:', detectedTextItem);
        
        if (detectedTextEl && detectedTextItem) {
            // Convertir en string si ce n'est pas déjà le cas
            let textStr = '';
            if (detectedText) {
                if (typeof detectedText === 'string') {
                    textStr = detectedText;
                } else if (typeof detectedText === 'object') {
                    textStr = JSON.stringify(detectedText);
                } else {
                    textStr = String(detectedText);
                }
            }
            
            // Toujours afficher quelque chose, même si le texte est vide
            const textToDisplay = textStr.trim() ? textStr : 'לא זוהה טקסט - אין טקסט';
            
            // Assigner le texte de plusieurs façons pour être sûr
            detectedTextEl.textContent = textToDisplay;
            detectedTextEl.innerText = textToDisplay;
            if (textToDisplay.includes('\n')) {
                detectedTextEl.innerHTML = textToDisplay.replace(/\n/g, '<br>');
            }
            
            // Forcer l'affichage avec tous les styles possibles
            detectedTextItem.style.display = 'block';
            detectedTextItem.style.visibility = 'visible';
            detectedTextEl.style.display = 'block';
            detectedTextEl.style.visibility = 'visible';
            detectedTextEl.style.opacity = '1';
            detectedTextEl.style.color = '#000000';
            detectedTextEl.style.fontSize = '1.2em';
            
            // Log pour déboguer APRÈS le traitement
            console.log('=== DÉBOGAGE TEXTE (APRÈS) ===');
            console.log('textStr:', textStr);
            console.log('textToDisplay:', textToDisplay);
            console.log('detectedTextEl.textContent:', detectedTextEl.textContent);
            console.log('detectedTextEl.innerText:', detectedTextEl.innerText);
            console.log('detectedTextEl.innerHTML:', detectedTextEl.innerHTML);
            console.log('Computed style display:', window.getComputedStyle(detectedTextEl).display);
            console.log('Computed style visibility:', window.getComputedStyle(detectedTextEl).visibility);
            console.log('Computed style color:', window.getComputedStyle(detectedTextEl).color);
            console.log('Computed style fontSize:', window.getComputedStyle(detectedTextEl).fontSize);
        } else {
            console.error('Éléments non trouvés:', {
                detectedTextEl: detectedTextEl,
                detectedTextItem: detectedTextItem,
                elementsDetectedText: this.elements.detectedText
            });
        }
        
        // Afficher les différences
        this.showDifferences(differences);
        
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
     * Affiche les différences trouvées entre le texte détecté et le texte de référence
     * @param {Array} differences - Liste des différences
     */
    showDifferences(differences) {
        const differencesInfoEl = document.getElementById('differencesInfo');
        if (!differencesInfoEl) {
            console.warn('Élément differencesInfo non trouvé');
            return;
        }
        
        if (!differences || differences.length === 0) {
            // Ne pas afficher de message ici - il est déjà affiché en haut
            // Afficher juste la légende
            let successText = '<div class="differences-explanation">';
            successText += '<div class="diff-legend">';
            successText += '<div class="legend-item"><span class="legend-color" style="background: #00ff00;"></span> כל האותיות נכונות</div>';
            successText += '</div>';
            successText += '</div>';
            
            differencesInfoEl.innerHTML = successText;
            differencesInfoEl.style.display = 'block';
            return;
        }
        
        // Compter les types de différences
        const missingCount = differences.filter(d => d.type === 'missing').length;
        const extraCount = differences.filter(d => d.type === 'extra').length;
        const wrongCount = differences.filter(d => d.type === 'wrong').length;
        
        // Créer le texte d'explication
        let explanationText = '<div class="differences-explanation">';
        explanationText += '<h4>הבדלים שנמצאו:</h4>';
        
        if (wrongCount > 0) {
            explanationText += `<div class="diff-item diff-wrong">`;
            explanationText += `<span class="diff-icon">🟠</span>`;
            explanationText += `<span class="diff-label">אותיות שגויות:</span>`;
            explanationText += `<span class="diff-count">${wrongCount}</span>`;
            explanationText += `</div>`;
            
            // Afficher les lettres fausses avec ce qui était attendu (cliquables)
            const wrongItems = differences.filter(d => d.type === 'wrong');
            wrongItems.forEach((item) => {
                const detected = item.text || '';
                const expected = item.expected || '';
                const rect = item.rect || null;
                const rectStr = rect ? JSON.stringify(rect) : '';
                
                explanationText += `<div class="diff-wrong-item" data-rect="${rectStr}" style="cursor: pointer;">`;
                explanationText += `<div class="diff-wrong-char">שגוי: <strong>${detected}</strong> (צריך להיות: <strong>${expected}</strong>)</div>`;
                explanationText += `</div>`;
            });
        }
        
        if (missingCount > 0) {
            explanationText += `<div class="diff-item diff-missing">`;
            explanationText += `<span class="diff-icon">🔴</span>`;
            explanationText += `<span class="diff-label">אותיות חסרות:</span>`;
            explanationText += `<span class="diff-count">${missingCount}</span>`;
            explanationText += `</div>`;
            
            // Afficher les lettres manquantes avec leur contexte
            const missingItems = differences.filter(d => d.type === 'missing');
            missingItems.forEach((item, idx) => {
                const missingChar = item.text || '';
                const contextBefore = item.context_before || '';
                const contextAfter = item.context_after || '';
                const markerPos = item.marker_position;
                
                explanationText += `<div class="diff-missing-item" data-marker-pos="${markerPos ? JSON.stringify(markerPos) : ''}">`;
                explanationText += `<div class="diff-missing-char">חסר: <strong>${missingChar}</strong></div>`;
                if (contextBefore || contextAfter) {
                    explanationText += `<div class="diff-context">`;
                    explanationText += `<span class="context-before">${contextBefore}</span>`;
                    explanationText += `<span class="context-missing">[${missingChar}]</span>`;
                    explanationText += `<span class="context-after">${contextAfter}</span>`;
                    explanationText += `</div>`;
                }
                explanationText += `</div>`;
            });
        }
        
        if (extraCount > 0) {
            explanationText += `<div class="diff-item diff-extra">`;
            explanationText += `<span class="diff-icon">🔵</span>`;
            explanationText += `<span class="diff-label">אותיות מיותרות:</span>`;
            explanationText += `<span class="diff-count">${extraCount}</span>`;
            explanationText += `</div>`;
            
            // Afficher les lettres en trop (cliquables)
            const extraItems = differences.filter(d => d.type === 'extra');
            extraItems.forEach((item) => {
                const extraChar = item.text || '';
                const rect = item.rect || null;
                const rectStr = rect ? JSON.stringify(rect) : '';
                
                explanationText += `<div class="diff-extra-item" data-rect="${rectStr}" style="cursor: pointer;">`;
                explanationText += `<div class="diff-extra-char">מיותר: <strong>${extraChar}</strong></div>`;
                explanationText += `</div>`;
            });
        }
        
        explanationText += '<div class="diff-legend">';
        explanationText += '<div class="legend-item"><span class="legend-color" style="background: #00ff00;"></span> אותיות נכונות</div>';
        if (wrongCount > 0) {
            explanationText += '<div class="legend-item"><span class="legend-color" style="background: #ffa500;"></span> אותיות שגויות</div>';
        }
        explanationText += '<div class="legend-item"><span class="legend-color" style="background: #ff0000;"></span> אותיות חסרות</div>';
        explanationText += '<div class="legend-item"><span class="legend-color" style="background: #0000ff;"></span> אותיות מיותרות</div>';
        explanationText += '</div>';
        explanationText += '</div>';
        
        differencesInfoEl.innerHTML = explanationText;
        differencesInfoEl.style.display = 'block';
        
        // Ajouter les écouteurs de clic pour tous les types d'erreurs
        this.setupMissingLetterClickHandlers();
        this.setupExtraLetterClickHandlers();
        this.setupWrongLetterClickHandlers();
    }
    
    /**
     * Configure les gestionnaires de clic pour les lettres manquantes
     * Permet de zoomer et centrer sur la position de la lettre manquante dans l'image
     */
    setupMissingLetterClickHandlers() {
        const missingItems = document.querySelectorAll('.diff-missing-item');
        missingItems.forEach((item) => {
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                const markerPosStr = item.getAttribute('data-marker-pos');
                if (markerPosStr && markerPosStr !== 'null' && markerPosStr !== '') {
                    try {
                        const markerPos = JSON.parse(markerPosStr);
                        if (markerPos && Array.isArray(markerPos) && markerPos.length === 4) {
                            // Centrer et zoomer sur la position du marqueur
                            this.zoomToPosition(markerPos[0], markerPos[1], markerPos[2], markerPos[3]);
                        }
                    } catch (e) {
                        console.error('Erreur lors du parsing de la position:', e);
                    }
                }
            });
        });
    }
    
    /**
     * Configure les gestionnaires de clic pour les lettres en plus
     * Permet de zoomer et centrer sur la position de la lettre en trop dans l'image
     */
    setupExtraLetterClickHandlers() {
        const extraItems = document.querySelectorAll('.diff-extra-item');
        extraItems.forEach((item) => {
            item.addEventListener('click', () => {
                const rectStr = item.getAttribute('data-rect');
                if (rectStr && rectStr !== 'null' && rectStr !== '') {
                    try {
                        const rect = JSON.parse(rectStr);
                        if (rect && Array.isArray(rect) && rect.length === 4) {
                            // Centrer et zoomer sur la position du rectangle
                            this.zoomToPosition(rect[0], rect[1], rect[2], rect[3]);
                        }
                    } catch (e) {
                        console.error('Erreur lors du parsing de la position:', e);
                    }
                }
            });
        });
    }
    
    /**
     * Configure les gestionnaires de clic pour les lettres fausses
     * Permet de zoomer et centrer sur la position de la lettre fausse dans l'image
     */
    setupWrongLetterClickHandlers() {
        const wrongItems = document.querySelectorAll('.diff-wrong-item');
        wrongItems.forEach((item) => {
            item.addEventListener('click', () => {
                const rectStr = item.getAttribute('data-rect');
                if (rectStr && rectStr !== 'null' && rectStr !== '') {
                    try {
                        const rect = JSON.parse(rectStr);
                        if (rect && Array.isArray(rect) && rect.length === 4) {
                            // Centrer et zoomer sur la position du rectangle
                            this.zoomToPosition(rect[0], rect[1], rect[2], rect[3]);
                        }
                    } catch (e) {
                        console.error('Erreur lors du parsing de la position:', e);
                    }
                }
            });
        });
    }
    
    /**
     * Zoom et centre sur une position spécifique dans l'image
     * @param {number} x - Position X du marqueur (coordonnées de l'image originale)
     * @param {number} y - Position Y du marqueur (coordonnées de l'image originale)
     * @param {number} w - Largeur du marqueur
     * @param {number} h - Hauteur du marqueur
     */
    zoomToPosition(x, y, w, h) {
        const imageViewer = this.elements.imageViewer;  // Le conteneur avec scroll
        const imageZoomContainer = this.elements.imageZoomContainer;  // Le conteneur de l'image
        const image = this.elements.displayImage;
        
        if (!imageViewer || !imageZoomContainer || !image || !image.naturalWidth || !image.naturalHeight) {
            return;
        }
        
        // Calculer le centre du marqueur dans l'image originale
        const centerX = x + w / 2;
        const centerY = y + h / 2;
        
        // Obtenir les dimensions du conteneur de zoom
        const zoomContainerWidth = imageZoomContainer.clientWidth || imageZoomContainer.offsetWidth;
        const zoomContainerHeight = imageZoomContainer.clientHeight || imageZoomContainer.offsetHeight;
        
        // Calculer le baseScale comme dans applyZoom()
        const baseScale = Math.min(
            zoomContainerWidth / image.naturalWidth,
            zoomContainerHeight / image.naturalHeight,
            1.0
        );
        
        // Calculer le zoom nécessaire pour voir le marqueur
        const scaleX = (zoomContainerWidth / (w * 3)) / baseScale;
        const scaleY = (zoomContainerHeight / (h * 3)) / baseScale;
        const newZoom = Math.max(1.0, Math.min(scaleX, scaleY, 3.0));
        
        // Appliquer le zoom
        this.zoomLevel = newZoom;
        this.applyZoom();
        
        // Attendre que le zoom soit appliqué
        setTimeout(() => {
            // Obtenir les dimensions réelles après le zoom
            const imgRect = image.getBoundingClientRect();
            const viewerRect = imageViewer.getBoundingClientRect();
            const containerRect = imageZoomContainer.getBoundingClientRect();
            const actualScale = baseScale * this.zoomLevel;
            
            // Dimensions de l'image zoomée
            const imageWidth = imgRect.width;
            const imageHeight = imgRect.height;
            const containerWidth = containerRect.width;
            const containerHeight = containerRect.height;
            
            // L'image est centrée horizontalement dans le conteneur
            // Calculer l'offset de centrage
            const imageOffsetXInContainer = (containerWidth - imageWidth) / 2;
            const imageOffsetYInContainer = 0; // L'image commence en haut
            
            // Calculer la position du marqueur dans l'image zoomée
            // L'image n'est pas inversée visuellement, on utilise centerX directement
            const markerXInImage = centerX * actualScale;
            const markerYInImage = centerY * actualScale;
            
            // Position du marqueur dans le conteneur (en tenant compte du centrage de l'image)
            const markerXInContainer = imageOffsetXInContainer + markerXInImage;
            const markerYInContainer = imageOffsetYInContainer + markerYInImage;
            
            // Position du conteneur dans le viewer (en tenant compte du scroll actuel)
            const containerLeftInViewer = containerRect.left - viewerRect.left + imageViewer.scrollLeft;
            const containerTopInViewer = containerRect.top - viewerRect.top + imageViewer.scrollTop;
            
            // Position absolue du marqueur dans le viewer
            const markerXInViewer = containerLeftInViewer + markerXInContainer;
            const markerYInViewer = containerTopInViewer + markerYInContainer;
            
            // Centrer le marqueur dans le viewer
            const viewerWidth = imageViewer.clientWidth;
            const viewerHeight = imageViewer.clientHeight;
            
            const targetScrollLeft = markerXInViewer - viewerWidth / 2;
            const targetScrollTop = markerYInViewer - viewerHeight / 2;
            
            // Limiter aux limites de scroll
            const maxScrollLeft = Math.max(0, imageViewer.scrollWidth - viewerWidth);
            const maxScrollTop = Math.max(0, imageViewer.scrollHeight - viewerHeight);
            
            const finalScrollLeft = Math.max(0, Math.min(maxScrollLeft, targetScrollLeft));
            const finalScrollTop = Math.max(0, Math.min(maxScrollTop, targetScrollTop));
            
            // Appliquer le scroll
            imageViewer.scrollLeft = finalScrollLeft;
            imageViewer.scrollTop = finalScrollTop;
            
            // Ajouter un effet visuel
            this.highlightPosition(x, y, w, h);
        }, 100);
    }
    
    /**
     * Met en évidence une position dans l'image avec un effet visuel
     * @param {number} x - Position X
     * @param {number} y - Position Y
     * @param {number} w - Largeur
     * @param {number} h - Hauteur
     */
    highlightPosition(x, y, w, h) {
        // Créer un élément de surbrillance temporaire
        let highlight = document.getElementById('missing-letter-highlight');
        if (!highlight) {
            highlight = document.createElement('div');
            highlight.id = 'missing-letter-highlight';
            highlight.style.cssText = `
                position: absolute;
                border: 3px solid #ff0000;
                background: rgba(255, 0, 0, 0.2);
                pointer-events: none;
                z-index: 1000;
                animation: pulse 1s ease-in-out 3;
            `;
            this.elements.imageZoomContainer.appendChild(highlight);
        }
        
        // Positionner le surligneur (en tenant compte du zoom et du scroll)
        const image = this.elements.displayImage;
        const imgRect = image.getBoundingClientRect();
        const containerRect = this.elements.imageZoomContainer.getBoundingClientRect();
        
        // Calculer la position relative à l'image zoomée
        const scaleX = imgRect.width / image.naturalWidth;
        const scaleY = imgRect.height / image.naturalHeight;
        
        highlight.style.left = `${(image.naturalWidth - x - w) * scaleX}px`;
        highlight.style.top = `${y * scaleY}px`;
        highlight.style.width = `${w * scaleX}px`;
        highlight.style.height = `${h * scaleY}px`;
        
        // Supprimer après l'animation
        setTimeout(() => {
            if (highlight && highlight.parentNode) {
                highlight.parentNode.removeChild(highlight);
            }
        }, 3000);
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
