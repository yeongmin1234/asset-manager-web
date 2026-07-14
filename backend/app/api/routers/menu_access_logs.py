from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.menu_access_log import MenuAccessLogCreate, MenuAccessLogCreateResponse
from app.services.menu_access_log_service import (
    MenuAccessDeniedError,
    MenuAccessPayloadError,
    record_menu_access_log,
)


router = APIRouter(prefix="/access-logs", tags=["access-logs"])


@router.post("/menu", response_model=MenuAccessLogCreateResponse)
def create_menu_access_log(
    payload: MenuAccessLogCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MenuAccessLogCreateResponse:
    try:
        return record_menu_access_log(db, request, user, payload)
    except MenuAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 가능한 메뉴가 아닙니다.") from exc
    except MenuAccessPayloadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="메뉴 정보가 올바르지 않습니다.") from exc
