from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes.alerts import router as alerts_router
from app.api.routes.health import router as health_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.telemetry import router as telemetry_router
from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="SmartHome API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

app.include_router(health_router)
app.include_router(sensors_router)
app.include_router(telemetry_router)
app.include_router(alerts_router)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/")
def root() -> dict:
    return {
        "name": "SmartHome API",
        "version": "0.3.0",
        "endpoints": [
            "/health",
            "/sensors",
            "/latest",
            "/history?sensor_id=<id>&limit=100",
            "/alerts",
            "/alert-summary",
            "/dashboard",
        ],
    }


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
