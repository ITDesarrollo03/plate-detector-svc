from typing import Optional
import pytesseract
import numpy as np
from app.ports.ocr_port import OcrPort


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
