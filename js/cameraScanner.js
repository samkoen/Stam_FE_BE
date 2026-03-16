/**
 * Prise de vue via le scanner de documents Capacitor (@capgo/capacitor-document-scanner).
 * Même contrat que takePhoto() : { file, displayUrl } ou null.
 * Sur web le plugin n'est en général pas dispo → retourne null (fallback caméra dans main).
 */
import {
  DocumentScanner,
  ResponseType,
  ScanDocumentResponseStatus
} from '@capgo/capacitor-document-scanner';
import { FileHandler } from './fileHandler.js';

function cleanBase64(str) {
  if (typeof str !== 'string') return '';
  let s = str.trim();
  if (s.includes(',')) s = s.split(',')[1] || s;
  return s.replace(/\s/g, '');
}

function base64ToFile(base64String, filename = 'scan.jpg') {
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
 * Ouvre le scanner de documents et retourne la première page comme fichier + URL d'affichage.
 * @returns {Promise<{file: File, displayUrl: string}|null>}
 */
export async function takePhotoWithScanner() {
  try {
    const result = await DocumentScanner.scanDocument({
      responseType: ResponseType.Base64,
      maxNumDocuments: 1,
      croppedImageQuality: 90,
      letUserAdjustCrop: true
    });

    if (result.status !== ScanDocumentResponseStatus.Success || !result.scannedImages?.length) {
      return null;
    }

    const firstBase64 = result.scannedImages[0];
    if (!firstBase64) return null;

    const file = base64ToFile(firstBase64, `scan_${Date.now()}.jpg`);
    const displayUrl = await FileHandler.base64ToDisplayUrl(firstBase64);
    return { file, displayUrl };
  } catch (err) {
    if (err?.message?.includes('cancel') || err?.message?.includes('not available')) {
      return null;
    }
    throw err;
  }
}
