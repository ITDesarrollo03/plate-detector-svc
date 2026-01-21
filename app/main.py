import os
from pathlib import Path
from fastapi import FastAPI
from app.api.routers import router
from app.core.config import settings

app = FastAPI(title="Plate Detector Service", version="1.0.0")

# Register Routers
app.include_router(router)

@app.on_event("startup")
def startup_event():
    # Create debug directory if it doesn't exist
    Path(settings.debug_dir).mkdir(parents=True, exist_ok=True)
    print(f"Debug directory: {settings.debug_dir}")

    # Validate YOLO model exists
    if not os.path.exists(settings.model_path):
        raise RuntimeError(f"YOLO model not found at {settings.model_path}")
    print(f"YOLO model loaded: {settings.model_path}")

    # Validate Tesseract is available
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
    except Exception as e:
        raise RuntimeError(f"Tesseract not available: {e}")
