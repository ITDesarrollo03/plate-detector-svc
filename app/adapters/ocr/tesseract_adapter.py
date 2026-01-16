from typing import Optional
import pytesseract
import numpy as np
from app.ports.ocr_port import OcrPort


class TesseractAdapter(OcrPort):
    def __init__(self, config: Optional[str] = None):
        self.config = config or r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    def extract_text(self, img: np.ndarray) -> str:
        return pytesseract.image_to_string(img, config=self.config)
