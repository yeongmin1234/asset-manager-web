"""Authenticated placeholders for online TEAM order management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.user import User
from app.schemas.order_management import OrderDashboardResponse, OrderListResponse, OrderManagementReady
from app.services.order_management_service import empty_dashboard, empty_list, ready_response


def require_order_access(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.role != "admin" and "online_order" not in (user.menu_permissions or []):
        raise HTTPException(status_code=403, detail="이 메뉴에 접근할 권한이 없습니다.")
    visibility = db.scalar(
        select(MenuVisibilitySetting.visible).where(MenuVisibilitySetting.menu_key == "online_order")
    )
    if visibility is False:
        raise HTTPException(status_code=403, detail="현재 숨김 처리된 메뉴입니다.")
    return user


router = APIRouter(
    prefix="/online/orders",
    tags=["online-orders"],
    dependencies=[Depends(require_order_access)],
)


@router.get("/dashboard", response_model=OrderDashboardResponse)
def get_dashboard() -> OrderDashboardResponse:
    return empty_dashboard()


@router.get("/preview", response_model=OrderListResponse)
def get_preview() -> OrderListResponse:
    return empty_list()


@router.post("/upload", dependencies=[Depends(require_admin)])
def upload_order_file() -> None:
    raise HTTPException(status_code=501, detail="파일 업로드 기능 준비 중")


@router.post("/process", dependencies=[Depends(require_admin)])
def process_order() -> None:
    raise HTTPException(status_code=501, detail="발주 가공 기능 준비 중")


@router.get("/result/{result_id}", response_model=OrderManagementReady)
def get_result(result_id: int) -> OrderManagementReady:
    return ready_response()


@router.get("/mappings", response_model=OrderListResponse)
def get_mappings() -> OrderListResponse:
    return empty_list()


@router.post("/mappings", dependencies=[Depends(require_admin)])
def save_mappings() -> None:
    raise HTTPException(status_code=501, detail="상품 매칭 수정 기능 준비 중")


@router.get("/history", response_model=OrderListResponse)
def get_history() -> OrderListResponse:
    return empty_list()


@router.get("/settings", response_model=OrderManagementReady)
def get_settings() -> OrderManagementReady:
    return ready_response()
