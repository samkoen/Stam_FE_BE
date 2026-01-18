"""
Module pour les méthodes de correction des erreurs de détection de lettres.
"""

from .base_correction import BaseCorrection, CorrectionResult
from .height_extension_correction import HeightExtensionCorrection
from .fusion_correction import FusionCorrection
from .reunification_correction import ReunificationCorrection
from .missing_letter_correction import MissingLetterCorrection
from .correction_manager import CorrectionManager

__all__ = [
    'BaseCorrection',
    'CorrectionResult',
    'HeightExtensionCorrection',
    'FusionCorrection',
    'ReunificationCorrection',
    'MissingLetterCorrection',
    'CorrectionManager'
]
