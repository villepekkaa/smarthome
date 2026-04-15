from fastapi import APIRouter

from app.api.services.telemetry_service import fetch_sensors

router = APIRouter(prefix="", tags=["sensors"])


@router.get("/sensors")
def sensors() -> dict:
    items = fetch_sensors()
    return {"count": len(items), "items": items}
