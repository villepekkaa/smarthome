from fastapi import APIRouter, HTTPException

from app.api.db import get_conn
from app.config import get_settings

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health() -> dict:
    try:
        conn = get_conn()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"status": "ok", "db_path": get_settings().db_path}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"health check failed: {exc}")
