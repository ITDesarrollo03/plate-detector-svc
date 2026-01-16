import numpy as np
import cv2

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
    # 1) Crop zona útil
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

def crop_with_padding(img_bgr: np.ndarray, x1, y1, x2, y2, pad: int = 10):
    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(img_bgr.shape[1], x2 + pad)
    y2p = min(img_bgr.shape[0], y2 + pad)
    return img_bgr[y1p:y2p, x1p:x2p]
