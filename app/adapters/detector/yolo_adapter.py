from ultralytics import YOLO
import numpy as np
from app.ports.detector_port import PlateDetectorPort
from app.domain.models import DetectionResult, BoundingBox
from app.core.config import settings

class YoloAdapter(PlateDetectorPort):
    def __init__(self):
        self.model = YOLO(settings.model_path)

    def detect_plate(self, img_bgr: np.ndarray) -> DetectionResult:
        results = self.model.predict(
            img_bgr,
            imgsz=settings.img_size,
            conf=settings.conf,
            verbose=False
        )[0]

        if results.boxes is None or len(results.boxes) == 0:
            return None

        best = max(results.boxes, key=lambda b: float(b.conf[0]))
        x1, y1, x2, y2 = map(int, best.xyxy[0])
        conf = float(best.conf[0])

        return DetectionResult(
            box=BoundingBox(x=x1, y=y1, w=x2-x1, h=y2-y1),
            confidence=conf
        )
