import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { FileHandler } from './fileHandler.js';

/**
 * Nettoie la chaîne base64 (préfixe data URL, espaces, retours à la ligne)
 */
function cleanBase64(str) {
  if (typeof str !== 'string') return '';
  let s = str.trim();
  if (s.includes(',')) s = s.split(',')[1] || s;
  return s.replace(/\s/g, '');
}

/**
 * Convertit une chaîne base64 en File
 * @param {string} base64String
 * @param {string} filename
 * @returns {File}
 */
function base64ToFile(base64String, filename = 'photo.jpg') {
  const clean = cleanBase64(base64String);
  const byteChars = atob(clean);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    byteNumbers[i] = byteChars.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: 'image/jpeg' });
  return new File([blob], filename, {
    type: 'image/jpeg',
    lastModified: Date.now()
  });
}

/**
 * Prend une photo avec @capacitor/camera (qualité 100).
 * L'utilisateur gère le flash via l'interface native de la caméra.
 * @returns {Promise<{file: File, displayUrl: string}|null>} Fichier + URL d'affichage, ou null si annulé/erreur
 */
export async function takePhoto() {
  try {
    const image = await Camera.getPhoto({
      quality: 100,
      allowEditing: false,
      resultType: CameraResultType.Base64,
      source: CameraSource.Camera
    });

    if (!image?.base64String) return null;
    const file = base64ToFile(image.base64String, `photo_${Date.now()}.jpg`);
    const displayUrl = await FileHandler.base64ToDisplayUrl(image.base64String);
    return { file, displayUrl };
  } catch (err) {
    if (err?.message?.includes('User cancelled') || err?.message?.includes('cancel')) {
      return null;
    }
    throw err;
  }
}
