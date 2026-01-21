from functools import lru_cache
import io
import os
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from app.ports.detector_port import PlateDetectorPort
from app.ports.ocr_port import OcrPort
from app.ports.info_extractor_port import InfoExtractorPort
from app.adapters.detector.yolo_adapter import YoloAdapter
from app.adapters.ocr.tesseract_adapter import TesseractPlateAdapter
from app.adapters.ocr.tesseract_document_adapter import TesseractDocumentAdapter
from app.adapters.extraction.regex_id_adapter import RegexIdAdapter
from app.domain import image_utils, services
from app.core.config import settings

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

    # Debug save always enabled for diagnosis
    debug_dir = settings.debug_dir
    os.makedirs(debug_dir, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    cv2.imwrite(f"{debug_dir}/{uid}_01_crop.jpg", plate)
    cv2.imwrite(f"{debug_dir}/{uid}_02_processed.jpg", thr)

    # 4) OCR con fallback si sale vacío
    raw_text = ocr_service.extract_text(thr).strip()
    print(f"DEBUG: Initial OCR raw_text: {raw_text!r}")
    
    if not raw_text:
        fallback_ocr = TesseractPlateAdapter(config="--oem 3 --psm 6 --dpi 300 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ")
        raw_text = fallback_ocr.extract_text(thr).strip()
        print(f"DEBUG: Fallback 1 raw_text: {raw_text!r}")
        
    if not raw_text:
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        raw_text = ocr_service.extract_text(gray).strip()
        print(f"DEBUG: Fallback 2 (gray) raw_text: {raw_text!r}")
        
    if not raw_text:
        raw_text = fallback_ocr.extract_text(cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)).strip()
        print(f"DEBUG: Fallback 3 (gray+config) raw_text: {raw_text!r}")

    # 5) Normalize
    plate_text = services.normalize_hn_plate(raw_text)
    print(f"DEBUG: Normalized text: {plate_text!r}")

    if not plate_text:
        # Error handling from original code
        print(f"ERROR: OCR failed to match pattern. Raw: {raw_text!r}")
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



@router.get("/debug/test")
def test_debug():
    """Test endpoint to verify debug routes are working"""
    return {"status": "ok", "message": "Debug endpoints are working"}


@router.get("/debug/images")
def list_debug_images():
    """List all debug images saved in debug directory"""
    debug_dir = settings.debug_dir
    try:
        if not os.path.exists(debug_dir):
            return {"files": [], "message": "Debug directory does not exist yet"}
        files = sorted(os.listdir(debug_dir))
        return {"files": files, "count": len(files), "directory": debug_dir}
    except Exception as e:
        return {"error": str(e), "files": []}


@router.get("/debug/images/{filename}")
def get_debug_image(filename: str):
    """Download a specific debug image"""
    # Sanitize filename to prevent directory traversal
    filename = os.path.basename(filename)
    file_path = f"{settings.debug_dir}/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    
    return FileResponse(file_path, media_type="image/jpeg", filename=filename)


@router.get("/debug/viewer", response_class=HTMLResponse)
def debug_viewer():
    """HTML page to view all debug images"""
    debug_dir = settings.debug_dir
    
    if not os.path.exists(debug_dir):
        files = []
    else:
        files = sorted(os.listdir(debug_dir), reverse=True)  # Most recent first
    
    # Group files by UID (first 8 chars before _)
    groups = {}
    for f in files:
        if '_' in f:
            uid = f.split('_')[0]
            if uid not in groups:
                groups[uid] = {}
            if '_01_crop' in f:
                groups[uid]['crop'] = f
            elif '_02_processed' in f:
                groups[uid]['processed'] = f
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Images Viewer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            h1 { color: #333; }
            .image-group { 
                background: white; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .image-group h3 { margin-top: 0; color: #666; }
            .images { display: flex; gap: 20px; flex-wrap: wrap; }
            .image-container { flex: 1; min-width: 300px; }
            .image-container h4 { margin: 10px 0; color: #444; }
            img { 
                max-width: 100%; 
                border: 2px solid #ddd; 
                border-radius: 4px;
                background: #000;
            }
            .no-images { color: #999; font-style: italic; }
        </style>
    </head>
    <body>
        <h1>🔍 Debug Images Viewer</h1>
        <p>Showing processed images from most recent to oldest</p>
    """
    
    if not groups:
        html += '<p class="no-images">No debug images found. Process an image first.</p>'
    else:
        for uid, imgs in groups.items():
            html += f'<div class="image-group"><h3>Image ID: {uid}</h3><div class="images">'
            
            if 'crop' in imgs:
                html += f'''
                <div class="image-container">
                    <h4>1. Cropped Plate (after deskew)</h4>
                    <img src="/debug/images/{imgs['crop']}" alt="Crop">
                </div>
                '''
            
            if 'processed' in imgs:
                html += f'''
                <div class="image-container">
                    <h4>2. Processed (sent to Tesseract)</h4>
                    <img src="/debug/images/{imgs['processed']}" alt="Processed">
                </div>
                '''
            
            html += '</div></div>'
    
    html += """
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)
