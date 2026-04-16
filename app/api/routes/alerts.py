from fastapi import APIRouter, Query

from app.api.services.alert_service import compute_alerts, summarize_alerts

router = APIRouter(prefix="", tags=["alerts"])


@router.get("/alerts")
def alerts(
    offline_min: int = Query(15, ge=1, le=1440),
    battery_low_mv: int = Query(2600, ge=1500, le=4000),
    humidity_warn_pct: float = Query(70.0, ge=0, le=100),
    temp_high_c: float = Query(28.0, ge=-50, le=120),
) -> dict:
    items = compute_alerts(
        offline_min=offline_min,
        battery_low_mv=battery_low_mv,
        humidity_warn_pct=humidity_warn_pct,
        temp_high_c=temp_high_c,
    )
    return {"count": len(items), "items": items}


@router.get("/alert-summary")
def alert_summary(
    offline_min: int = Query(15, ge=1, le=1440),
    battery_low_mv: int = Query(2600, ge=1500, le=4000),
    humidity_warn_pct: float = Query(70.0, ge=0, le=100),
    temp_high_c: float = Query(28.0, ge=-50, le=120),
) -> dict:
    items = compute_alerts(
        offline_min=offline_min,
        battery_low_mv=battery_low_mv,
        humidity_warn_pct=humidity_warn_pct,
        temp_high_c=temp_high_c,
    )
    return summarize_alerts(items)
