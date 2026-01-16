from typing import Protocol
import numpy as np

class OcrPort(Protocol):
    def extract_text(self, img: np.ndarray) -> str:
        ...
