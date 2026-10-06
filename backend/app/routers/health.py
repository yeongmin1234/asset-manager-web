from typing import Dict

from fastapi import APIRouter

from app.db.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def database_health_check() -> Dict[str, str]:
    is_connected, _ = check_database_connection()
    return {"status": "ok" if is_connected else "error"}
