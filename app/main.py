from fastapi import FastAPI
from app.api.routers import router
from app.core.config import settings

app = FastAPI(title="Plate Detector Service", version="1.0.0")

# Register Routers
app.include_router(router)

@app.on_event("startup")
def startup_event():
    pass
