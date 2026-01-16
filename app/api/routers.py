from functools import lru_cache
import io
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.ports.detector_port import PlateDetectorPort
from app.ports.ocr_port import OcrPort
from app.adapters.detector.yolo_adapter import YoloAdapter
from app.adapters.ocr.tesseract_adapter import TesseractAdapter
from app.domain import image_utils, services

router = APIRouter()

# Dependency Injection (Cached)
@lru_cache()
def get_detector() -> PlateDetectorPort:
    return YoloAdapter()

@lru_cache()
def get_ocr() -> OcrPort:
    return TesseractAdapter()

@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    detector: PlateDetectorPort = Depends(get_detector)
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPG/PNG/WEBP supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    result = detector.detect_plate(img)
    if not result:
        raise HTTPException(status_code=404, detail="No plate detected")

    # Crop logic for display check
    x1, y1, w, h = result.box.x, result.box.y, result.box.w, result.box.h
    x2, y2 = x1 + w, y1 + h
    plate = img[y1:y2, x1:x2]

    if plate.size == 0:
        raise HTTPException(status_code=500, detail="Detector returned invalid crop")

    success, buffer = cv2.imencode(".jpg", plate)
    if not success:
        raise HTTPException(status_code=500, detail="Could not encode image")

    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": "attachment; filename=plate.jpg"}
    )

@router.post("/ocr", response_model=dict)
async def ocr(
    file: UploadFile = File(...),
    detector: PlateDetectorPort = Depends(get_detector),
    ocr_service: OcrPort = Depends(get_ocr)
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPG/PNG/WEBP supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    # 1) Detect
    result = detector.detect_plate(img)
    if not result:
        # Replicating original behavior: maybe 404? 
        # The original code threw 404 inside detect_plate helper.
        raise HTTPException(status_code=404, detail="No plate detected")

    x1, y1, w, h = result.box.x, result.box.y, result.box.w, result.box.h
    x2, y2 = x1 + w, y1 + h

    # 2) Crop with padding
    plate = image_utils.crop_with_padding(img, x1, y1, x2, y2, pad=10)
    if plate is None or plate.size == 0:
        raise HTTPException(status_code=500, detail="Detector returned invalid crop for OCR")

    # 3) Preprocess
    try:
        thr = image_utils.preprocess_for_ocr(plate)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # 4) OCR
    raw_text = ocr_service.extract_text(thr).strip()

    # 5) Normalize
    plate_text = services.normalize_hn_plate(raw_text)

    if not plate_text:
        # Error handling from original code
        raise HTTPException(status_code=422, detail=f"OCR did not match Honduras format (AAA####). raw={raw_text!r}")

    return {
        "fileName": file.filename,
        "plateText": plate_text,
        "rawText": raw_text,
        "detConf": result.confidence,
        "bbox": {"x": x1, "y": y1, "w": w, "h": h}
    }
