from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import numpy as np
import cv2
import io
import re
import pytesseract
from .settings import settings


# =========================
# Helpers (OCR / limpieza)
# =========================

HN_PLATE_RE = re.compile(r'([A-Z]{3})\s*([0-9]{4})')

LETTER_FIX = str.maketrans({
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "6": "G",
    "8": "B",
})

DIGIT_FIX = str.maketrans({
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "B": "8",
})


def clean_alnum_upper(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def normalize_hn_plate(raw_text: str) -> str:
    """
    Extrae/normaliza placa Honduras: AAA####  -> 'AAA 1234'
    Aplica correcciones de confusiones letras/números según posición.
    """
    cleaned = clean_alnum_upper(raw_text)
    if not cleaned:
        return ""

    # 1) Intenta encontrar patrón directamente dentro del texto
    m = HN_PLATE_RE.search(cleaned)
    if m:
        letters = m.group(1)
        digits = m.group(2)
        return f"{letters} {digits}"

    # 2) Si no match, intenta rescatar: toma los primeros 7 alfanum si hay
    # (útil cuando tesseract mete basura antes/después)
    if len(cleaned) < 7:
        return ""

    # Busca cualquier ventana de 7 chars que pueda convertirse
    for i in range(0, len(cleaned) - 6):
        chunk = cleaned[i:i+7]  # 3 + 4
        lpart = chunk[:3]
        dpart = chunk[3:]

        # Corrige por posición:
        # primeras 3 deben ser letras
        lpart = lpart.translate(LETTER_FIX)
        # últimas 4 deben ser dígitos
        dpart = dpart.translate(DIGIT_FIX)

        if re.fullmatch(r"[A-Z]{3}", lpart) and re.fullmatch(r"\d{4}", dpart):
            return f"{lpart} {dpart}"

    return ""


def crop_lr_by_projection(bin_img: np.ndarray, margin: int = 6, min_col_frac: float = 0.01):
    if bin_img is None or bin_img.size == 0:
        return bin_img

    h, w = bin_img.shape[:2]
    if h < 5 or w < 5:
        return bin_img

    b = (bin_img > 0).astype(np.uint8)
    col_sum = b.sum(axis=0)
    thresh = max(1, int(h * min_col_frac))

    cols = np.where(col_sum >= thresh)[0]
    if cols.size == 0:
        return bin_img

    x_min = int(max(0, cols[0] - margin))
    x_max = int(min(w, cols[-1] + margin + 1))
    return bin_img[:, x_min:x_max]


def crop_bbox_text(bin_img: np.ndarray, pad: int = 4, min_area: int = 80):
    b = (bin_img > 0).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return bin_img

    cnts = [c for c in cnts if cv2.contourArea(c) >= min_area]
    if not cnts:
        return bin_img

    x, y, w, h = cv2.boundingRect(np.vstack(cnts))
    H, W = bin_img.shape[:2]

    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(W, x + w + pad)
    y2 = min(H, y + h + pad)

    return bin_img[y1:y2, x1:x2]


def shave_lr_edges(bin_img: np.ndarray, edge_white_frac: float = 0.55, max_shave: int = 200):
    if bin_img is None or bin_img.size == 0:
        return bin_img

    h, w = bin_img.shape[:2]
    b = (bin_img > 0).astype(np.uint8)
    col_frac = b.mean(axis=0)

    left = 0
    shaved = 0
    while left < w - 1 and col_frac[left] >= edge_white_frac and shaved < max_shave:
        left += 1
        shaved += 1

    right = w - 1
    shaved = 0
    while right > 0 and col_frac[right] >= edge_white_frac and shaved < max_shave:
        right -= 1
        shaved += 1

    if right - left < 10:
        return bin_img

    return bin_img[:, left:right+1]


def preprocess_for_ocr(plate_bgr: np.ndarray) -> np.ndarray:
    """
    Devuelve binaria lista para OCR (texto blanco, fondo negro).
    """
    # 1) Crop zona útil (ajusta si tu cámara varía)
    h, w = plate_bgr.shape[:2]
    plate = plate_bgr[int(h * 0.28):int(h * 0.80), :]

    # 2) Escala
    plate = cv2.resize(plate, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    # 3) Gray + blur
    gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 4) Threshold invertido (texto blanco)
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31, 10
    )

    # 5) Morph close/open
    thr = cv2.morphologyEx(
        thr,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
        iterations=2
    )
    thr = cv2.morphologyEx(
        thr,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1
    )

    # 6) Quitar marcos LR + recortes
    thr = shave_lr_edges(thr, edge_white_frac=0.55, max_shave=200)
    thr = crop_lr_by_projection(thr, margin=8, min_col_frac=0.01)
    thr = crop_bbox_text(thr, pad=6, min_area=120)

    return thr


# =========================
# App + Model
# =========================

app = FastAPI(title="Plate Detector Service", version="1.0.0")
model = None


@app.on_event("startup")
def load_model():
    global model
    model = YOLO(settings.model_path)


def detect_plate(img_bgr: np.ndarray):
    results = model.predict(
        img_bgr,
        imgsz=settings.img_size,
        conf=settings.conf,
        verbose=False
    )[0]

    if results.boxes is None or len(results.boxes) == 0:
        raise HTTPException(status_code=404, detail="No plate detected")

    best = max(results.boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])
    conf = float(best.conf[0])

    return x1, y1, x2, y2, conf


def crop_with_padding(img_bgr: np.ndarray, x1, y1, x2, y2, pad: int = 10):
    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(img_bgr.shape[1], x2 + pad)
    y2p = min(img_bgr.shape[0], y2 + pad)
    return img_bgr[y1p:y2p, x1p:x2p]


# =========================
# Endpoints
# =========================

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    data = await file.read()
    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    x1, y1, x2, y2, conf = detect_plate(img)
    plate = img[y1:y2, x1:x2]

    success, buffer = cv2.imencode(".jpg", plate)
    if not success:
        raise HTTPException(status_code=500, detail="Could not encode image")

    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": "attachment; filename=plate.jpg"}
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

    # 1) YOLO detect
    x1, y1, x2, y2, det_conf = detect_plate(img)

    # 2) Crop con padding
    plate = crop_with_padding(img, x1, y1, x2, y2, pad=10)

    # 3) Prepro OCR
    thr = preprocess_for_ocr(plate)

    # Debug (opcional)
    cv2.imwrite("/tmp/plate_ocr_ready_cropped.jpg", thr)

    # 4) OCR
    tess_cfg = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    raw_text = pytesseract.image_to_string(thr, config=tess_cfg)

    # 5) Normaliza / valida Honduras + corrige confusiones
    plate_text = normalize_hn_plate(raw_text)

    if not plate_text:
        # si quieres que falle cuando no cumple formato:
        raise HTTPException(status_code=422, detail=f"OCR did not match Honduras format (AAA####). raw={raw_text!r}")

    return {
        "fileName": file.filename,
        "plateText": plate_text,      # "AAA 1234"
        "rawText": raw_text,          # útil para debug
        "detConf": det_conf,
        "bbox": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
    }
