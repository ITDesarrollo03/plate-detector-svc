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



def deskew_plate(img_bgr: np.ndarray) -> np.ndarray:
    """
    Corrects the skew of the plate image using contour analysis on character candidates.
    Conservative approach to avoid over-rotation.
    """
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr

    h_img, w_img = img_bgr.shape[:2]
    
    # Skip deskewing for very small images
    if h_img < 30 or w_img < 60:
        return img_bgr
    
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Use adaptive threshold to handle shadows/gradients better than global Otsu
    # Invert so text is white (foreground)
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        19, 9
    )

    # Find contours
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(cnts) < 3:  # Need at least 3 character-like contours for reliable deskew
        return img_bgr
    
    # Filter for character-like contours
    merged_pts = []
    
    min_h = h_img * 0.15  # Lowered from 0.2 for more flexibility
    max_h = h_img * 0.95
    min_area = 50  # Minimum area to avoid noise
    
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
            
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / float(h) if h > 0 else 0
        
        # Filter noise: 
        # - Height must be significant (character sized)
        # - Aspect ratio reasonable for a letter/digit
        if h > min_h and h < max_h and 0.15 < aspect < 2.5:
            merged_pts.append(c)
            
    if len(merged_pts) < 3:  # Need at least 3 valid character contours
        return img_bgr
        
    # Combine valid contours
    all_points = np.vstack(merged_pts)
    rect = cv2.minAreaRect(all_points)
    center, size, angle = rect

    # Correct angle logic
    # OpenCV's minAreaRect returns angle in [-90, 0)
    # We want to align the longest side horizontally
    width, height = size
    if width < height:
        angle = angle + 90
    
    # Normalize angle to [-45, 45] range
    if angle > 45:
        angle = angle - 90
    elif angle < -45:
        angle = angle + 90
        
    # VERY conservative: only correct small tilts (max 10 degrees)
    # Ignore rotations that are too small or too large
    if abs(angle) < 0.5 or abs(angle) > 10.0:
        return img_bgr

    # Apply rotation
    image_center = (w_img // 2, h_img // 2)
    M = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    
    rotated = cv2.warpAffine(
        img_bgr, M, (w_img, h_img), 
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated



def preprocess_for_ocr(plate_bgr: np.ndarray) -> np.ndarray:
    """
    Returns a binary image ready for OCR (white text on black background).
    """
    if plate_bgr is None or plate_bgr.size == 0:
        raise ValueError("Empty plate image for OCR preprocessing")

    # 0) Deskew (straighten) the plate before cropping vertical bands
    plate_bgr = deskew_plate(plate_bgr)

    # 1) Crop useful band of the plate (avoid top/bottom borders)
    # More aggressive crop to exclude "HONDURAS" text at top and "CENTROAMERICA" at bottom
    h, w = plate_bgr.shape[:2]
    plate = plate_bgr[int(h * 0.30):int(h * 0.75), :]

    # 2) Upscale to help OCR
    plate = cv2.resize(plate, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)

    # 3) Gray + blur
    gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Unsharp mask to recover edges
    sharp = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 1.0), -0.5, 0)

    # Boost contrast slightly
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    sharp = clahe.apply(sharp)

    # 4) Threshold inverted (text as white)
    # Reduced block size and C value for cleaner edges
    thr_adapt = cv2.adaptiveThreshold(
        sharp, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        25, 5  # Changed from 35, 7 to get sharper edges
    )
    # Otsu fallback
    _, thr_otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Pick the one with better balance (closer to 0.5 foreground ratio)
    def balance_score(img):
        p = img.mean() / 255.0
        return abs(0.5 - p)
    thr = thr_adapt if balance_score(thr_adapt) < balance_score(thr_otsu) else thr_otsu

    # 5) Morph operations - BALANCED approach
    # Small CLOSE to connect broken characters (numbers with cuts)
    # Then OPEN to remove small noise
    thr = cv2.morphologyEx(
        thr,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),  # Very small kernel
        iterations=1
    )
    thr = cv2.morphologyEx(
        thr,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
        iterations=1
    )

    # 6) Trim lateral borders and keep only text region
    thr = shave_lr_edges(thr, edge_white_frac=0.55, max_shave=200)
    thr = crop_lr_by_projection(thr, margin=8, min_col_frac=0.01)
    thr = crop_bbox_text(thr, pad=6, min_area=120)

    if thr is None or thr.size == 0:
        raise ValueError("OCR preprocessing returned an empty image")

    return thr


def crop_with_padding(img_bgr: np.ndarray, x1, y1, x2, y2, pad: int = 10):
    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(img_bgr.shape[1], x2 + pad)
    y2p = min(img_bgr.shape[0], y2 + pad)
    return img_bgr[y1p:y2p, x1p:x2p]


def preprocess_document_for_ocr(img_bgr: np.ndarray) -> np.ndarray:
    """
    Preprocesa documentos (DNI/licencia) para OCR de texto general.
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Empty document image for OCR preprocessing")

    # Escala para ganar resolución
    img = cv2.resize(img_bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=40, sigmaSpace=40)

    # Threshold suave para mantener espacios
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35, 15
    )

    # Inverción si hay fondo claro con texto oscuro? Probamos a mantener original
    return thr
