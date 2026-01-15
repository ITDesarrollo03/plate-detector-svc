from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO
import numpy as np
import cv2
import base64
from .settings import settings

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

    # tomamos la mejor detección (mayor confianza)
    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])

    plate = img[y1:y2, x1:x2]

    # codificar a base64
    _, buffer = cv2.imencode(".jpg", plate)
    plate_b64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "fileName": file.filename,
        "plate": plate_b64,
        "conf": float(best.conf[0]),
        "bbox": {
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1
        }
    }
