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

    # mejor detección
    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])

    plate = img[y1:y2, x1:x2]

    # convertir a JPG en memoria
    success, buffer = cv2.imencode(".jpg", plate)
    if not success:
        raise HTTPException(status_code=500, detail="Could not encode image")

    image_bytes = io.BytesIO(buffer.tobytes())

    headers = {
        "Content-Disposition": "attachment; filename=plate.jpg"
    }

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

    # 1) Detectar placa con YOLO (igual que tu lógica actual)
    try:
        results = model.predict(img, imgsz=settings.img_size, conf=settings.conf, verbose=False)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    if results.boxes is None or len(results.boxes) == 0:
        raise HTTPException(status_code=404, detail="No plate detected")

    # Mejor detección
    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])
    plate = img[y1:y2, x1:x2]

    # 2) Preprocesado OCR (importante)
    gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3) OCR con Tesseract
    config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    text = pytesseract.image_to_string(thr, config=config)

    # Limpieza del texto
    text = "".join(ch for ch in text.upper() if ch.isalnum())

    return {
        "fileName": file.filename,
        "plateText": text,
        "detConf": float(best.conf[0]),
        "bbox": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
    }
