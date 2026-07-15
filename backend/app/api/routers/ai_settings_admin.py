from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.services.audit_log_service import record_audit_log


router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


class AiSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=100)
    timeout_seconds: Optional[float] = Field(default=None, ge=1, le=60)
    fallback_enabled: Optional[bool] = None


def _read():
    return {
        "enabled": settings.ai_enabled,
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "timeout_seconds": settings.ai_timeout_seconds,
        "fallback_enabled": settings.ai_fallback_enabled,
        "api_key_configured": bool(settings.ai_api_key.strip()),
        "storage": "process_memory",
    }


@router.get("/settings")
def read_ai_settings():
    return _read()


@router.put("/settings")
def update_ai_settings(payload: AiSettingsUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = payload.dict(exclude_none=True)
    if "provider" in values and values["provider"].strip() != "openai_compatible":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="지원하지 않는 AI provider입니다.")
    mapping = {"enabled": "ai_enabled", "provider": "ai_provider", "model": "ai_model", "timeout_seconds": "ai_timeout_seconds", "fallback_enabled": "ai_fallback_enabled"}
    for key, value in values.items():
        setattr(settings, mapping[key], value.strip() if isinstance(value, str) else value)
    record_audit_log(db, request, user, action_type="update", menu_key="settings", menu_name="AI 설정", target_type="ai_settings", target_id=None, target_name="자연어 AI 설정", action_summary="자연어 AI 설정을 변경했습니다.", after_data={key: value for key, value in values.items()})
    db.commit()
    return _read()
