import pytesseract
import numpy as np
from typing import Optional
from app.ports.ocr_port import OcrPort


class TesseractDocumentAdapter(OcrPort):
    """
    OCR para documentos (DNI/Licencia) usando layout de párrafos.
    """
    def __init__(self, config: Optional[str] = None):
        # preserve_interword_spaces mantiene separación de palabras útil para regex
        self.config = config or r"--oem 3 --psm 6 -l spa+eng -c preserve_interword_spaces=1"

    def extract_text(self, img: np.ndarray) -> str:
        return pytesseract.image_to_string(img, config=self.config)
