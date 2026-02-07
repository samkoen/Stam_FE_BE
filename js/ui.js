/**
 * Module de gestion de l'interface utilisateur
 */
import { translateParachaName } from './config.js';

export class UIManager {
    constructor() {
        this.elements = {
            uploadSection: document.getElementById('uploadSection'),
            uploadArea: document.getElementById('uploadArea'),
            uploadBtnSmall: document.getElementById('uploadBtnSmall'),
            fileInput: document.getElementById('fileInput'),
            fileInfo: document.getElementById('fileInfo'),
            fileInfoSmall: document.getElementById('fileInfoSmall'),
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
            rightPanel: document.getElementById('rightResultsPanel'),
            leftPanel: document.getElementById('leftImagePanel'),
            panelTitle: document.getElementById('panelTitleRight'),
            panelTitleLeft: document.getElementById('panelTitleLeft'),
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
            differencesInfo: document.getElementById('differencesInfo'),
            showSpaceErrors: document.getElementById('showSpaceErrors'),
            filterSpacesContainer: document.getElementById('filterSpacesContainer'),
            panelResizer: document.getElementById('panelResizer')
        };
        this.isExpanded = false;
        this.zoomLevel = 1.0;
        this.lastDifferences = []; // Stocker les différences pour le filtrage
        
        // Listener pour la checkbox de filtrage des espaces
        if (this.elements.showSpaceErrors) {
            this.elements.showSpaceErrors.addEventListener('change', () => {
                if (this.lastDifferences) {
                    this.showDifferences(this.lastDifferences);
                    
                    // Mettre à jour aussi le résumé des erreurs si possible
                    // (nécessite de recalculer les comptes filtrés, fait dans showDifferences mais pas mis à jour dans le header status-pill)
                    // Pour l'instant on met juste à jour la liste.
                }
            });
        }
    }

    /**
     * Affiche les informations du fichier sélectionné
     * @param {File} file - Fichier sélectionné
     * @param {Function} formatFileSize - Fonction pour formater la taille
     */
    showFileInfo(file, formatFileSize) {
        const fileInfo = this.elements.fileInfo;
        if (fileInfo) {
            fileInfo.innerHTML = `
                <div class="file-name">📄 ${file.name}</div>
                <div class="file-size">גודל: ${formatFileSize(file.size)}</div>
            `;
            fileInfo.classList.add('active');
        }
        
        // Mettre à jour aussi le petit affichage
        const fileInfoSmall = this.elements.fileInfoSmall;
        if (fileInfoSmall) {
            fileInfoSmall.textContent = file.name;
        }
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
        this.lastDifferences = differences || [];
        
        this.elements.displayImage.src = `data:image/jpeg;base64,${imageBase64}`;
        this.elements.displayImage.style.display = 'block';
        this.elements.imageZoomContainer.style.display = 'block';
        this.elements.imagePlaceholder.style.display = 'none';
        this.elements.panelTitle.textContent = parachaName ? 'תוצאות הניתוח' : 'זיהוי אותיות';
        
        // Afficher la checkbox de filtrage si on a des résultats
        if (this.elements.filterSpacesContainer) {
            this.elements.filterSpacesContainer.style.display = parachaName ? 'block' : 'none';
        }
        
        // Traduire le nom de la paracha en hébreu
        this.elements.parachaName.textContent = translateParachaName(parachaName);
        
        // Statut global (complete / incomplete) et erreurs
        const parachaStatusEl = document.getElementById('parachaStatus');
        const errorsStatusEl = document.getElementById('errorsStatus');
        
        let hasRealErrors = false;
        if (errors) {
            hasRealErrors = (errors.missing || 0) + (errors.extra || 0) + (errors.wrong || 0) > 0;
        } else if (differences && differences.length > 0) {
            // Filtrer les espaces si nécessaire pour déterminer s'il y a de "vraies" erreurs
            // Ici on considère tout ce qui est dans differences comme erreur par défaut
            hasRealErrors = true;
        }

        // Déterminer la classe CSS du statut pour l'appliquer aussi à "ללא שגיאות"
        let statusClass = 'info-value status-pill';
        
        if (parachaStatusEl) {
            // Si il y a des erreurs, afficher le message selon si complete ou incomplete
            if (hasRealErrors) {
                if (parachaStatus === 'complete') {
                    parachaStatusEl.textContent = 'פרשה שלמה עם טעיות';
                } else {
                    parachaStatusEl.textContent = 'פרשה חלקית עם טעיות';
                }
                statusClass = 'info-value status-pill status-error'; // Rouge pour les erreurs
                parachaStatusEl.className = statusClass;
            } else if (parachaStatus === 'complete') {
                parachaStatusEl.textContent = 'פרשה שלמה תקינה';
                statusClass = 'info-value status-pill status-success'; // Vert pour complète valide
                parachaStatusEl.className = statusClass;
            } else if (parachaStatus === 'incomplete') {
                parachaStatusEl.textContent = 'פרשה חלקית תקינה';
                statusClass = 'info-value status-pill status-partial'; // Bleu distinct pour partielle valide
                parachaStatusEl.className = statusClass;
            } else {
                parachaStatusEl.textContent = '';
                parachaStatusEl.className = 'info-value status-pill';
            }
        }
        if (errorsStatusEl) {
            if (hasErrors === false) {
                errorsStatusEl.textContent = 'ללא שגיאות';
                errorsStatusEl.className = statusClass; // Utiliser la même couleur que le statut
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
                // Utiliser la même classe CSS que le statut pour la cohérence des couleurs
                const statusClassForMessage = statusClass || 'info-value status-pill status-success';
                successMessageEl.innerHTML = `<span class="${statusClassForMessage}">✅ התוצאה מושלמת! 100% התאמה</span>`;
                successMessageEl.style.display = 'inline-block';
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
     * Met à jour les overlays pour les erreurs d'espaces sur l'image
     */
    updateSpaceErrorOverlays() {
        // Supprimer les overlays existants
        const existingOverlays = this.elements.imageZoomContainer.querySelectorAll('.space-error-overlay');
        existingOverlays.forEach(el => el.remove());
        
        // Vérifier si on doit afficher les erreurs d'espaces
        const showSpaces = this.elements.showSpaceErrors ? this.elements.showSpaceErrors.checked : false;
        if (!showSpaces || !this.lastDifferences) return;
        
        const image = this.elements.displayImage;
        if (!image || !image.naturalWidth) return;
        
        const imgRect = image.getBoundingClientRect();
        // Eviter division par zéro
        if (image.naturalWidth === 0 || image.naturalHeight === 0) return;
        
        const scaleX = imgRect.width / image.naturalWidth;
        const scaleY = imgRect.height / image.naturalHeight;
        const imgLeft = image.offsetLeft;
        const imgTop = image.offsetTop;
        
        this.lastDifferences.forEach(diff => {
            // Filtrer pour ne prendre que les erreurs d'espaces
            const isSpaceError = (diff.type === 'missing' || diff.type === 'extra') && 
                                 (!diff.text || diff.text.trim() === '' || diff.text === ' ');
            
            if (isSpaceError && diff.marker_position) {
                const [x, y, w, h] = diff.marker_position;
                
                const overlay = document.createElement('div');
                overlay.className = 'space-error-overlay';
                overlay.style.position = 'absolute';
                overlay.style.border = '2px solid red';
                overlay.style.left = `${imgLeft + x * scaleX}px`;
                overlay.style.top = `${imgTop + y * scaleY}px`;
                overlay.style.width = `${w * scaleX}px`;
                overlay.style.height = `${h * scaleY}px`;
                overlay.style.pointerEvents = 'none'; // Laisser passer les clics
                overlay.style.zIndex = '10'; // Au-dessus de l'image
                
                this.elements.imageZoomContainer.appendChild(overlay);
            }
        });
    }

    /**
     * Affiche les différences trouvées entre le texte détecté et le texte de référence
     * @param {Array} differences - Liste des différences
     */
    showDifferences(differences) {
        // Sauvegarder les différences pour les mises à jour ultérieures (zoom, filtre)
        this.lastDifferences = differences;
        // Mettre à jour les overlays
        this.updateSpaceErrorOverlays();

        const differencesInfoEl = document.getElementById('differencesInfo');
        if (!differencesInfoEl) {
            console.warn('Élément differencesInfo non trouvé');
            return;
        }
        
        // Filtrage des erreurs d'espaces
        const showSpaces = this.elements.showSpaceErrors ? this.elements.showSpaceErrors.checked : false;
        
        const filteredDifferences = (differences || []).filter(d => {
            if (showSpaces) return true;
            
            // Masquer les erreurs qui sont UNIQUEMENT des espaces (missing ou extra)
            // Un espace peut être représenté par ' ' ou une chaîne qui ne contient que des espaces
            const isSpaceError = (d.type === 'missing' || d.type === 'extra') && 
                                 (!d.text || d.text.trim() === '' || d.text === ' ');
            
            if (isSpaceError) {
                return false;
            }
            return true;
        });
        
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
        
        // Identifier les erreurs d'espaces (pour les exclure des compteurs de lettres)
        const isSpaceError = (d) => {
            const isSpace = (d.text === ' ' || (d.text && d.text.trim() === ''));
            return (d.type === 'missing' || d.type === 'extra') && isSpace;
        };
        
        // Compter les erreurs d'espaces
        const spaceErrors = filteredDifferences.filter(isSpaceError);
        const spaceErrorsCount = spaceErrors.length;
        
        // Compter les types de différences (FILTRÉES, en EXCLUANT les erreurs d'espaces)
        const missingCount = filteredDifferences.filter(d => d.type === 'missing' && !isSpaceError(d)).length;
        const extraCount = filteredDifferences.filter(d => d.type === 'extra' && !isSpaceError(d)).length;
        const wrongCount = filteredDifferences.filter(d => d.type === 'wrong').length;
        
        // Mettre à jour le résumé des erreurs dans le header (optionnel mais mieux)
        const errorsStatusEl = document.getElementById('errorsStatus');
        if (errorsStatusEl) {
             const letterErrorsTotal = missingCount + extraCount + wrongCount;
             
             // Si on a des erreurs de lettres OU (des erreurs d'espaces ET qu'on veut les voir)
             if (letterErrorsTotal > 0 || (showSpaces && spaceErrorsCount > 0)) {
                 let statusText = `שגיאות: ${letterErrorsTotal} (חסר ${missingCount}, מיותר ${extraCount}, שגוי ${wrongCount})`;
                 
                 if (showSpaces && spaceErrorsCount > 0) {
                     statusText += ` + ${spaceErrorsCount} רווחים`;
                 }
                 
                 errorsStatusEl.textContent = statusText;
                 errorsStatusEl.className = 'info-value status-pill status-error';
             } 
             // Si on n'a pas d'erreurs de lettres visibles, mais qu'il y a des différences (donc des espaces cachés)
             else if (differences.length > 0 && !showSpaces) {
                 // Vérifier s'il y a vraiment des différences cachées (espaces)
                 // On peut le savoir car filteredDifferences est vide ou ne contient pas d'espaces, 
                 // mais differences en contient.
                 const rawSpaceErrors = differences.filter(d => {
                     const isSpace = (d.text === ' ' || (d.text && d.text.trim() === ''));
                     return (d.type === 'missing' || d.type === 'extra') && isSpace;
                 }).length;
                 
                 if (rawSpaceErrors > 0) {
                     errorsStatusEl.textContent = 'שגיאות רווחים (מוסתר)';
                     errorsStatusEl.className = 'info-value status-pill status-warning';
                 } else {
                     // Cas rare : différences qui ne sont ni lettres ni espaces (ne devrait pas arriver avec la logique actuelle)
                     errorsStatusEl.textContent = 'ללא שגיאות';
                     errorsStatusEl.className = 'info-value status-pill status-success';
                 }
             } else {
                 errorsStatusEl.textContent = 'ללא שגיאות';
                 errorsStatusEl.className = 'info-value status-pill status-success';
             }
        }
        
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
            const wrongItems = filteredDifferences.filter(d => d.type === 'wrong');
            wrongItems.forEach((item) => {
                const detected = item.text || '';
                const expected = item.expected || '';
                const contextBefore = item.context_before || '';
                const contextAfter = item.context_after || '';
                const rect = item.rect || null;
                const rectStr = rect ? JSON.stringify(rect) : '';
                
                explanationText += `<div class="diff-wrong-item" data-rect="${rectStr}" style="cursor: pointer;">`;
                explanationText += `<div class="diff-wrong-char">שגוי: <strong>${detected}</strong> (צריך להיות: <strong>${expected}</strong>)</div>`;
                
                if (contextBefore || contextAfter) {
                    explanationText += `<div class="diff-context">`;
                    explanationText += `<span class="context-before">${contextBefore}</span>`;
                    explanationText += `<span class="context-wrong" style="color: #ffa500; font-weight: bold;">[${detected}]</span>`;
                    explanationText += `<span class="context-after">${contextAfter}</span>`;
                    explanationText += `</div>`;
                }
                
                explanationText += `</div>`;
            });
        }
        
        if (missingCount > 0) {
            explanationText += `<div class="diff-item diff-missing">`;
            explanationText += `<span class="diff-icon">🔴</span>`;
            explanationText += `<span class="diff-label">אותיות חסרות:</span>`;
            explanationText += `<span class="diff-count">${missingCount}</span>`;
            explanationText += `</div>`;
            
            // Afficher les lettres manquantes avec leur contexte (exclure les espaces)
            const missingItems = filteredDifferences.filter(d => d.type === 'missing' && !isSpaceError(d));
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
            
            // Afficher les lettres en trop (cliquables, exclure les espaces)
            const extraItems = filteredDifferences.filter(d => d.type === 'extra' && !isSpaceError(d));
            extraItems.forEach((item) => {
                const extraChar = item.text || '';
                const contextBefore = item.context_before || '';
                const contextAfter = item.context_after || '';
                const rect = item.rect || null;
                const rectStr = rect ? JSON.stringify(rect) : '';
                
                explanationText += `<div class="diff-extra-item" data-rect="${rectStr}" style="cursor: pointer;">`;
                explanationText += `<div class="diff-extra-char">מיותר: <strong>${extraChar}</strong></div>`;
                
                if (contextBefore || contextAfter) {
                    explanationText += `<div class="diff-context">`;
                    explanationText += `<span class="context-before">${contextBefore}</span>`;
                    explanationText += `<span class="context-extra" style="color: #0000ff; font-weight: bold;">[${extraChar}]</span>`;
                    explanationText += `<span class="context-after">${contextAfter}</span>`;
                    explanationText += `</div>`;
                }
                
                explanationText += `</div>`;
            });
        }
        
        // Afficher les erreurs d'espaces si la checkbox est cochée
        if (showSpaces && spaceErrorsCount > 0) {
            const missingSpaces = spaceErrors.filter(d => d.type === 'missing');
            const extraSpaces = spaceErrors.filter(d => d.type === 'extra');
            
            explanationText += `<div class="diff-item diff-space" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">`;
            explanationText += `<span class="diff-icon">⚪</span>`;
            explanationText += `<span class="diff-label">שגיאות רווחים:</span>`;
            explanationText += `<span class="diff-count">${spaceErrorsCount}</span>`;
            explanationText += `</div>`;
            
            // Afficher les espaces manquants
            if (missingSpaces.length > 0) {
                explanationText += `<div class="diff-subsection" style="margin-left: 20px; margin-top: 10px;">`;
                explanationText += `<div class="diff-subtitle">רווחים חסרים (${missingSpaces.length}):</div>`;
                missingSpaces.forEach((item) => {
                    const contextBefore = item.context_before || '';
                    const contextAfter = item.context_after || '';
                    const markerPos = item.marker_position;
                    const markerPosStr = markerPos ? JSON.stringify(markerPos) : '';
                    
                    explanationText += `<div class="diff-space-item" data-marker-pos="${markerPosStr}" style="cursor: pointer; margin: 5px 0; padding: 5px; background: #ffe6e6; border-radius: 4px;">`;
                    explanationText += `<div class="diff-space-char">חסר רווח</div>`;
                    if (contextBefore || contextAfter) {
                        explanationText += `<div class="diff-context">`;
                        explanationText += `<span class="context-before">${contextBefore}</span>`;
                        explanationText += `<span class="context-missing" style="color: #ff0000; font-weight: bold;">[ ]</span>`;
                        explanationText += `<span class="context-after">${contextAfter}</span>`;
                        explanationText += `</div>`;
                    }
                    explanationText += `</div>`;
                });
                explanationText += `</div>`;
            }
            
            // Afficher les espaces en trop
            if (extraSpaces.length > 0) {
                explanationText += `<div class="diff-subsection" style="margin-left: 20px; margin-top: 10px;">`;
                explanationText += `<div class="diff-subtitle">רווחים מיותרים (${extraSpaces.length}):</div>`;
                extraSpaces.forEach((item) => {
                    const contextBefore = item.context_before || '';
                    const contextAfter = item.context_after || '';
                    const markerPos = item.marker_position;
                    const rect = item.rect || null;
                    const markerPosStr = markerPos ? JSON.stringify(markerPos) : '';
                    const rectStr = rect ? JSON.stringify(rect) : '';
                    
                    explanationText += `<div class="diff-space-item" data-marker-pos="${markerPosStr}" data-rect="${rectStr}" style="cursor: pointer; margin: 5px 0; padding: 5px; background: #e6f3ff; border-radius: 4px;">`;
                    explanationText += `<div class="diff-space-char">מיותר רווח</div>`;
                    if (contextBefore || contextAfter) {
                        explanationText += `<div class="diff-context">`;
                        explanationText += `<span class="context-before">${contextBefore}</span>`;
                        explanationText += `<span class="context-extra" style="color: #0000ff; font-weight: bold;">[ ]</span>`;
                        explanationText += `<span class="context-after">${contextAfter}</span>`;
                        explanationText += `</div>`;
                    }
                    explanationText += `</div>`;
                });
                explanationText += `</div>`;
            }
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
        this.setupSpaceErrorClickHandlers();
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
     * Configure les gestionnaires de clic pour les erreurs d'espaces
     * Permet de zoomer et centrer sur la position de l'erreur d'espace dans l'image
     */
    setupSpaceErrorClickHandlers() {
        const spaceItems = document.querySelectorAll('.diff-space-item');
        spaceItems.forEach((item) => {
            item.addEventListener('click', () => {
                // Essayer d'abord avec marker_position
                const markerPosStr = item.getAttribute('data-marker-pos');
                if (markerPosStr && markerPosStr !== 'null' && markerPosStr !== '') {
                    try {
                        const markerPos = JSON.parse(markerPosStr);
                        if (markerPos && Array.isArray(markerPos) && markerPos.length === 4) {
                            // Centrer et zoomer sur la position du marqueur
                            this.zoomToPosition(markerPos[0], markerPos[1], markerPos[2], markerPos[3]);
                            return;
                        }
                    } catch (e) {
                        console.error('Erreur lors du parsing de la position du marqueur:', e);
                    }
                }
                
                // Fallback sur rect si disponible
                const rectStr = item.getAttribute('data-rect');
                if (rectStr && rectStr !== 'null' && rectStr !== '') {
                    try {
                        const rect = JSON.parse(rectStr);
                        if (rect && Array.isArray(rect) && rect.length === 4) {
                            // Centrer et zoomer sur la position du rectangle
                            this.zoomToPosition(rect[0], rect[1], rect[2], rect[3]);
                        }
                    } catch (e) {
                        console.error('Erreur lors du parsing de la position du rectangle:', e);
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
        
        // Calculer le zoom nécessaire pour voir le marqueur (avec un minimum pour que l'erreur soit bien visible)
        const scaleX = (zoomContainerWidth / (w * 3)) / baseScale;
        const scaleY = (zoomContainerHeight / (h * 3)) / baseScale;
        const computedZoom = Math.min(scaleX, scaleY, 3.0);
        const newZoom = Math.max(1.8, Math.max(1.0, computedZoom));
        
        // Appliquer le zoom
        this.zoomLevel = newZoom;
        this.applyZoom();
        
        // Attendre que le zoom soit appliqué
        setTimeout(() => {
            // Recalculer le scale réel (au cas où l'arrondi ou les scrollbars jouent)
            const imgRect = image.getBoundingClientRect();
            // Si l'image n'est pas affichée ou largeur nulle, éviter division par zéro
            if (imgRect.width === 0 || image.naturalWidth === 0) return;
            
            const actualScale = imgRect.width / image.naturalWidth;
            
            // Position de l'image par rapport au container
            // Cela prend en compte le margin: auto ou l'alignement flex
            const imgLeft = image.offsetLeft;
            const imgTop = image.offsetTop;
            
            // Position du container par rapport au viewer
            const containerLeft = imageZoomContainer.offsetLeft;
            const containerTop = imageZoomContainer.offsetTop;
            
            // Position du marqueur relative à l'image
            const markerXInImage = centerX * actualScale;
            const markerYInImage = centerY * actualScale;
            
            // Position absolue du marqueur dans l'espace de scroll du viewer
            const absoluteMarkerX = containerLeft + imgLeft + markerXInImage;
            const absoluteMarkerY = containerTop + imgTop + markerYInImage;
            
            // Dimensions de la zone visible du viewer
            const viewerWidth = imageViewer.clientWidth;
            const viewerHeight = imageViewer.clientHeight;
            
            // Calcul du scroll pour centrer
            const targetScrollLeft = absoluteMarkerX - viewerWidth / 2;
            const targetScrollTop = absoluteMarkerY - viewerHeight / 2;
            
            // Appliquer le scroll (le navigateur gère le clamping min/max)
            imageViewer.scrollLeft = targetScrollLeft;
            imageViewer.scrollTop = targetScrollTop;
            
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
        
        // Position de l'image dans le conteneur (gère le margin: auto ou flex align)
        const imgLeft = image.offsetLeft;
        const imgTop = image.offsetTop;
        
        // Positionner par rapport au conteneur (qui est en position: relative)
        highlight.style.left = `${imgLeft + x * scaleX}px`;
        highlight.style.top = `${imgTop + y * scaleY}px`;
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

                // Gestion du centrage/alignement pour permettre le scroll
                // Si l'image est plus large que le conteneur, on aligne à gauche
                // sinon on centre
                if (newWidth > containerWidth) {
                    container.style.justifyContent = 'flex-start';
                    img.style.margin = '0'; 
                } else {
                    container.style.justifyContent = 'center';
                    img.style.margin = '0 auto';
                }
                
                // Mettre à jour les overlays d'erreurs d'espaces
                this.updateSpaceErrorOverlays();
            } else {
                // Si les dimensions naturelles ne sont pas encore disponibles, attendre le chargement
                // L'événement 'load' se chargera d'appliquer le zoom
            }
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
            if (this.elements.detectLettersBtn) {
                this.elements.detectLettersBtn.classList.add('loading');
                this.elements.detectLettersBtn.disabled = true;
            }
        } else {
            this.elements.loadingSection.classList.remove('active');
            if (this.elements.detectLettersBtn) {
                this.elements.detectLettersBtn.classList.remove('loading');
                // Ne pas réactiver automatiquement ici, laisser l'appelant gérer si nécessaire
                // ou réactiver si on suppose que la fin du chargement rend la main
                this.elements.detectLettersBtn.disabled = false;
            }
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
            if (this.elements.uploadArea) {
                this.elements.uploadArea.classList.add('dragover');
            }
        } else {
            if (this.elements.uploadArea) {
                this.elements.uploadArea.classList.remove('dragover');
            }
        }
    }

    /**
     * Bascule l'état d'agrandissement du panneau de droite
     */
    toggleExpand() {
        if (!this.elements.expandBtn) return;
        
        this.isExpanded = !this.isExpanded;
        if (this.isExpanded) {
            if (this.elements.rightPanel) {
                this.elements.rightPanel.classList.add('expanded');
            }
            this.elements.expandBtn.textContent = '⛶';
            this.elements.expandBtn.title = 'Réduire';
        } else {
            if (this.elements.rightPanel) {
                this.elements.rightPanel.classList.remove('expanded');
            }
            this.elements.expandBtn.textContent = '⛶';
            this.elements.expandBtn.title = 'Agrandir';
        }
    }

    /**
     * Réinitialise l'interface
     */
    reset() {
        if (this.elements.fileInfo) {
            this.elements.fileInfo.classList.remove('active');
        }
        if (this.elements.fileInfoSmall) {
            this.elements.fileInfoSmall.textContent = '';
        }
        this.elements.fileInput.value = '';
        this.setDetectLettersButtonEnabled(false);
        this.showLoading(false);
        this.hideError();
        this.resetImageDisplay();
        this.elements.resetBtn.style.display = 'none';
        
        // Nettoyage supplémentaire des résultats
        if (this.elements.detectedText) this.elements.detectedText.textContent = '';
        const detectedTextItem = document.getElementById('detectedTextItem');
        if (detectedTextItem) detectedTextItem.style.display = 'none';
        
        const differencesInfo = document.getElementById('differencesInfo');
        if (differencesInfo) {
            differencesInfo.innerHTML = '';
            differencesInfo.style.display = 'none';
        }
        
        if (this.elements.filterSpacesContainer) {
            this.elements.filterSpacesContainer.style.display = 'none';
        }
        
        const parachaStatusEl = document.getElementById('parachaStatus');
        if (parachaStatusEl) {
            parachaStatusEl.textContent = '';
            parachaStatusEl.className = 'info-value status-pill';
        }
        
        const errorsStatusEl = document.getElementById('errorsStatus');
        if (errorsStatusEl) {
            errorsStatusEl.textContent = '';
            errorsStatusEl.className = 'info-value status-pill';
        }
        
        const successMessageEl = document.getElementById('successMessage');
        if (successMessageEl) {
            successMessageEl.style.display = 'none';
        }
        
        // Supprimer les overlays d'erreur
        const existingOverlays = this.elements.imageZoomContainer.querySelectorAll('.space-error-overlay');
        existingOverlays.forEach(el => el.remove());
        
        this.lastDifferences = [];
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
