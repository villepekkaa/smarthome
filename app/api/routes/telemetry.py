from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.services.telemetry_service import fetch_history, fetch_latest

router = APIRouter(prefix="", tags=["telemetry"])


@router.get("/latest")
def latest(sensor_id: Optional[str] = None) -> dict:
    items = fetch_latest(sensor_id=sensor_id)

    if sensor_id and not items:
        raise HTTPException(status_code=404, detail=f"sensor not found: {sensor_id}")

    if sensor_id and items:
        return items[0]

    return {"count": len(items), "items": items}


@router.get("/history")
def history(
    sensor_id: str = Query(..., description="sensor_id, e.g. ruuvi_c7ebd8f6f019"),
    limit: int = Query(100, ge=1, le=5000),
) -> dict:
    items = fetch_history(sensor_id=sensor_id, limit=limit)
    return {"sensor_id": sensor_id, "count": len(items), "items": items}
