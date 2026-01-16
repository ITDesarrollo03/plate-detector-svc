from pydantic import BaseModel
from typing import List, Optional

class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int

class DetectionResult(BaseModel):
    box: BoundingBox
    confidence: float
    plate_image: Optional[bytes] = None  # Encoded image (e.g., jpg) for return if needed

class OcrResult(BaseModel):
    file_name: str
    plate_text: str
    raw_text: str
    detection_confidence: float
    bbox: BoundingBox
