import pytesseract
import numpy as np
from app.ports.ocr_port import OcrPort

class TesseractAdapter(OcrPort):
    def extract_text(self, img: np.ndarray) -> str:
        tess_cfg = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return pytesseract.image_to_string(img, config=tess_cfg)
