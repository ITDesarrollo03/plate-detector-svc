from typing import Optional
import numpy as np
from ultralytics import YOLO
from app.ports.detector_port import PlateDetectorPort
from app.domain.models import DetectionResult, BoundingBox
from app.core.config import settings


class YoloAdapter(PlateDetectorPort):
    def __init__(self):
        self.model = YOLO(settings.model_path)

    def detect_plate(self, img_bgr: np.ndarray) -> Optional[DetectionResult]:
        results = self.model.predict(
            img_bgr,
            imgsz=settings.img_size,
            conf=settings.conf,
            verbose=False
        )[0]

        if results.boxes is None or len(results.boxes) == 0:
            return None

        boxes = results.boxes
        conf_arr = boxes.conf.cpu().numpy().reshape(-1)
        best_idx = int(conf_arr.argmax())
        best = boxes[best_idx]
        x1, y1, x2, y2 = map(float, best.xyxy[0])
        conf = float(best.conf[0])

        img_h, img_w = img_bgr.shape[:2]
        x1 = max(0, min(int(x1), img_w - 1))
        y1 = max(0, min(int(y1), img_h - 1))
        x2 = max(x1 + 1, min(int(x2), img_w))
        y2 = max(y1 + 1, min(int(y2), img_h))

        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            return None

        return DetectionResult(
            box=BoundingBox(x=x1, y=y1, w=width, h=height),
            confidence=conf
        )
