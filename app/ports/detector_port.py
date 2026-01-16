from typing import Protocol
import numpy as np
from app.domain.models import DetectionResult

class PlateDetectorPort(Protocol):
    def detect_plate(self, img_bgr: np.ndarray) -> DetectionResult:
        ...
