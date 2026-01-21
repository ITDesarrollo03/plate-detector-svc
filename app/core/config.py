from pydantic import BaseModel
import os
import tempfile
from pathlib import Path

class Settings(BaseModel):
    model_path: str = os.getenv("MODEL_PATH", "models/plate-detector.pt")
    conf: float = float(os.getenv("CONF", "0.25"))
    img_size: int = int(os.getenv("IMG_SIZE", "640"))

    # Cross-platform debug directory configuration
    debug_dir: str = os.getenv(
        "DEBUG_DIR",
        str(Path(tempfile.gettempdir()) / "debug_plates")
    )

settings = Settings()
