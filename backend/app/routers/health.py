from typing import Dict

from fastapi import APIRouter

from app.db.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "asset-manager-backend",
    }


@router.get("/health/db")
def database_health_check() -> Dict[str, str]:
    is_connected, message = check_database_connection()
    if is_connected:
        return {
            "status": "ok",
            "database": "connected",
        }

    return {
        "status": "error",
        "database": "disconnected",
        "message": message or "Database connection failed",
    }
