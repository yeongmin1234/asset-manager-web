from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.user import User
from app.schemas.menu_visibility import MenuVisibilityResponse, MenuVisibilityUpdate
from app.services.audit_log_service import record_audit_log


router = APIRouter(prefix="/menu-visibility", tags=["menu-visibility"])

MENU_NAMES = {
    "dashboard": "대시보드", "drink_orders": "음료주문기록", "work_manual": "업무설명서",
    "vendor_contacts": "업체연락처", "expiration_schedules": "점검·만료 관리", "assets": "자산 관리",
    "software": "SW 현황", "company_cars": "법인차량 관리", "fire_insurance": "파주화재보험",
    "network": "네트워크 현황", "excel_management": "엑셀 관리", "statistics": "통계 / 리포트",
    "history": "변경 이력", "install_files": "설치자료실", "hr_list": "인사업무 리스트", "scm": "SCM",
    "user_management": "사용자 관리", "settings": "설정",
}
ALWAYS_VISIBLE_MENU_KEYS = {"dashboard", "assets", "settings"}


def _response(db: Session) -> MenuVisibilityResponse:
    stored = {row.menu_key: row.visible for row in db.scalars(select(MenuVisibilitySetting)).all()}
    return MenuVisibilityResponse(visibility={key: True if key in ALWAYS_VISIBLE_MENU_KEYS else stored.get(key, True) for key in MENU_NAMES})


@router.get("", response_model=MenuVisibilityResponse)
def get_menu_visibility(db: Session = Depends(get_db)) -> MenuVisibilityResponse:
    return _response(db)


@router.patch("/{menu_key}", response_model=MenuVisibilityResponse)
def update_menu_visibility(
    menu_key: str, payload: MenuVisibilityUpdate, request: Request,
    db: Session = Depends(get_db), current_admin: User = Depends(require_admin),
) -> MenuVisibilityResponse:
    if menu_key not in MENU_NAMES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 사이드바 메뉴입니다.")
    if menu_key in ALWAYS_VISIBLE_MENU_KEYS and not payload.visible:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="항상 표시되는 메뉴는 숨길 수 없습니다.")

    row = db.scalar(select(MenuVisibilitySetting).where(MenuVisibilitySetting.menu_key == menu_key))
    old_visible = True if row is None or menu_key in ALWAYS_VISIBLE_MENU_KEYS else row.visible
    if row is None:
        row = MenuVisibilitySetting(menu_key=menu_key, visible=payload.visible)
        db.add(row)
    else:
        row.visible = payload.visible
    db.commit()

    if old_visible != payload.visible:
        menu_name = MENU_NAMES[menu_key]
        record_audit_log(
            db, request, current_admin, action_type="update", menu_key="settings", menu_name="설정",
            target_type="menu_visibility", target_id=None, target_name=menu_name,
            action_summary="사이드바 메뉴 '{}'를 {} 처리했습니다.".format(menu_name, "표시" if payload.visible else "숨김"),
            before_data={"menu_key": menu_key, "visible": old_visible},
            after_data={"menu_key": menu_key, "visible": payload.visible}, changed_fields=["visible"],
        )
    return _response(db)
