from typing import Optional
import os
import pytesseract
import numpy as np
from app.ports.ocr_port import OcrPort

# Configure Tesseract executable path for Windows
if os.name == 'nt':  # Windows
    tesseract_cmd = os.getenv(
        'TESSERACT_CMD',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    )
    if os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


class TesseractPlateAdapter(OcrPort):
    """
    OCR especializado para placas (texto corto, mayúsculas, dígitos y guiones).
    """
    def __init__(self, config: Optional[str] = None):
        self.config = config or r"--oem 3 --psm 7 --dpi 300 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- "

    def extract_text(self, img: np.ndarray) -> str:
        return pytesseract.image_to_string(img, config=self.config)


# Alias de compatibilidad si hubiera usos previos
TesseractAdapter = TesseractPlateAdapter
