from functools import lru_cache
import io
import os
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.ports.detector_port import PlateDetectorPort
from app.ports.ocr_port import OcrPort
from app.ports.info_extractor_port import InfoExtractorPort
from app.adapters.detector.yolo_adapter import YoloAdapter
from app.adapters.ocr.tesseract_adapter import TesseractPlateAdapter
from app.adapters.ocr.tesseract_document_adapter import TesseractDocumentAdapter
from app.adapters.extraction.regex_id_adapter import RegexIdAdapter
from app.domain import image_utils, services

router = APIRouter()

# Dependency Injection (Cached)
@lru_cache()
def get_detector() -> PlateDetectorPort:
    return YoloAdapter()

@lru_cache()
def get_plate_ocr() -> OcrPort:
    return TesseractPlateAdapter()

@lru_cache()
def get_doc_ocr() -> OcrPort:
    return TesseractDocumentAdapter()

@lru_cache()
def get_id_extractor() -> InfoExtractorPort:
    return RegexIdAdapter()

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
    ocr_service: OcrPort = Depends(get_plate_ocr)
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

    # Debug save if enabled
    if os.getenv("DEBUG_SAVE_PLATE"):
        uid = uuid.uuid4().hex[:8]
        cv2.imwrite(f"/tmp/plate_crop_{uid}.jpg", plate)
        cv2.imwrite(f"/tmp/plate_ocr_ready_{uid}.jpg", thr)

    # 4) OCR con fallback si sale vacío
    raw_text = ocr_service.extract_text(thr).strip()
    if not raw_text:
        fallback_ocr = TesseractPlateAdapter(config="--oem 3 --psm 6 --dpi 300 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ")
        raw_text = fallback_ocr.extract_text(thr).strip()
    if not raw_text:
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        raw_text = ocr_service.extract_text(gray).strip()
    if not raw_text:
        raw_text = fallback_ocr.extract_text(cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)).strip()

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


@router.post("/extract-info", response_model=dict)
async def extract_info(
    file: UploadFile = File(...),
    ocr_service: OcrPort = Depends(get_doc_ocr),
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

    # OCR on RGB image
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    raw_text = ocr_service.extract_text(rgb).strip()
    if not raw_text:
        raise HTTPException(status_code=422, detail="OCR returned empty text")

    payload = services.parse_dispatch_info(raw_text)

    return {
        "fileName": file.filename,
        "rawText": raw_text,
        "payload": payload,
    }


def _validate_image_upload(file: UploadFile):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPG/PNG/WEBP supported")


async def _process_identity_document(
    file: UploadFile,
    ocr_service: OcrPort,
    extractor: InfoExtractorPort,
):
    _validate_image_upload(file)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    try:
        doc = image_utils.preprocess_document_for_ocr(img)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    ocr_text = ocr_service.extract_text(doc).strip()
    if not ocr_text:
        # Fallback: intenta sin preprocesado
        ocr_text = ocr_service.extract_text(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).strip()
        if not ocr_text:
            raise HTTPException(status_code=422, detail="OCR returned empty text")

    payload = extractor.extract(ocr_text)
    return {
        "fileName": file.filename,
        "ocr_text": ocr_text,
        "identity": payload.get("identity"),
        "identityFormatted": payload.get("identityFormatted"),
        "full_name": payload.get("full_name"),
        "payload": payload,
    }


@router.post("/dni/extract", response_model=dict)
async def extract_dni(
    file: UploadFile = File(...),
    ocr_service: OcrPort = Depends(get_doc_ocr),
    extractor: InfoExtractorPort = Depends(get_id_extractor),
):
    return await _process_identity_document(file, ocr_service, extractor)


@router.post("/license/extract", response_model=dict)
async def extract_license(
    file: UploadFile = File(...),
    ocr_service: OcrPort = Depends(get_doc_ocr),
    extractor: InfoExtractorPort = Depends(get_id_extractor),
):
    return await _process_identity_document(file, ocr_service, extractor)
