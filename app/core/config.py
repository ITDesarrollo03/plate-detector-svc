from pydantic import BaseModel
import os

class Settings(BaseModel):
    model_path: str = os.getenv("MODEL_PATH", "models/plate-detector.pt")
    conf: float = float(os.getenv("CONF", "0.25"))
    img_size: int = int(os.getenv("IMG_SIZE", "640"))

settings = Settings()
