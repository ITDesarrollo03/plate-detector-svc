from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import numpy as np
import cv2
import io
from .settings import settings
import pytesseract

app = FastAPI(title="Plate Detector Service", version="1.0.0")
model = None


@app.on_event("startup")
def load_model():
    global model
    model = YOLO(settings.model_path)


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    data = await file.read()
    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    results = model.predict(
        img,
        imgsz=settings.img_size,
        conf=settings.conf,
        verbose=False
    )[0]

    if results.boxes is None or len(results.boxes) == 0:
        raise HTTPException(status_code=404, detail="No plate detected")

    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])

    plate = img[y1:y2, x1:x2]

    success, buffer = cv2.imencode(".jpg", plate)
    if not success:
        raise HTTPException(status_code=500, detail="Could not encode image")

    image_bytes = io.BytesIO(buffer.tobytes())

    headers = {"Content-Disposition": "attachment; filename=plate.jpg"}

    return StreamingResponse(
        image_bytes,
        media_type="image/jpeg",
        headers=headers
    )


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPG/PNG/WEBP supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    # 1) Detectar placa con YOLO
    try:
        results = model.predict(
            img,
            imgsz=settings.img_size,
            conf=settings.conf,
            verbose=False
        )[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    if results.boxes is None or len(results.boxes) == 0:
        raise HTTPException(status_code=404, detail="No plate detected")

    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])

    # 2) Recorte con padding para no cortar caracteres
    pad = 10
    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(img.shape[1], x2 + pad)
    y2p = min(img.shape[0], y2 + pad)
    plate = img[y1p:y2p, x1p:x2p]

    # =========================
    # PREPROCESADO OCR FINAL
    # =========================

    # 1) Recortar zona útil (quitar franja azul y texto pequeño)
    h, w = plate.shape[:2]
    plate = plate[int(h * 0.28):int(h * 0.80), :]

    # 2) Escalar (muy importante)
    plate = cv2.resize(plate, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    # 3) Grayscale
    gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)

    # 4) Blur
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 5) Threshold INVERSO (letras BLANCAS)
    thr = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        10
    )

    # 6) Rellenar letras (CLAVE)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 7) Limpiar ruido pequeño
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)

    # Debug
    cv2.imwrite("/tmp/plate_ocr_ready.jpg", thr)

    # 10) OCR con Tesseract
    config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    text = pytesseract.image_to_string(thr, config=config)

    # Limpieza
    text = "".join(ch for ch in text.upper() if ch.isalnum())

    return {
        "fileName": file.filename,
        "plateText": text,
        "detConf": float(best.conf[0]),
        "bbox": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
    }
