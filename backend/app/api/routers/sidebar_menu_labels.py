from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.database import get_db
from app.models.sidebar_menu_label import SidebarMenuLabel
from app.models.user import User
from app.schemas.sidebar_menu_label import SidebarMenuLabelsResponse, SidebarMenuLabelUpdate
from app.services.audit_log_service import record_audit_log


router = APIRouter(prefix="/sidebar-menu-labels", tags=["sidebar-menu-labels"])

MENU_NAMES = {
    "dashboard": "대시보드", "drink_orders": "음료주문기록", "work_manual": "업무설명서",
    "vendor_contacts": "업체연락처", "expiration_schedules": "점검·만료 관리", "assets": "자산 관리",
    "software": "SW 현황", "company_cars": "법인차량 관리", "fire_insurance": "파주화재보험",
    "network": "네트워크 현황", "excel_management": "엑셀 관리", "statistics": "통계 / 리포트",
    "history": "변경 이력", "install_files": "설치자료실", "hr_list": "리스트", "scm": "SCM",
    "user_management": "사용자 관리", "settings": "설정",
}


@router.get("", response_model=SidebarMenuLabelsResponse)
def get_sidebar_menu_labels(db: Session = Depends(get_db)) -> SidebarMenuLabelsResponse:
    rows = db.scalars(select(SidebarMenuLabel)).all()
    return SidebarMenuLabelsResponse(labels={row.menu_key: row.menu_name for row in rows})


@router.patch("/{menu_key}", response_model=SidebarMenuLabelsResponse)
def update_sidebar_menu_label(
    menu_key: str,
    payload: SidebarMenuLabelUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> SidebarMenuLabelsResponse:
    if menu_key not in MENU_NAMES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 사이드바 메뉴입니다.")

    row = db.scalar(select(SidebarMenuLabel).where(SidebarMenuLabel.menu_key == menu_key))
    old_name = row.menu_name if row is not None else MENU_NAMES[menu_key]
    if row is None:
        row = SidebarMenuLabel(menu_key=menu_key, menu_name=payload.menu_name)
        db.add(row)
    else:
        row.menu_name = payload.menu_name
    db.commit()

    if old_name != payload.menu_name:
        record_audit_log(
            db, request, current_admin, action_type="update", menu_key="settings", menu_name="설정",
            target_type="sidebar_menu_label", target_id=None, target_name=old_name,
            action_summary="사이드바 메뉴 이름을 '{}'에서 '{}'로 변경했습니다.".format(old_name, payload.menu_name),
            before_data={"menu_key": menu_key, "menu_name": old_name},
            after_data={"menu_key": menu_key, "menu_name": payload.menu_name}, changed_fields=["menu_name"],
        )

    rows = db.scalars(select(SidebarMenuLabel)).all()
    return SidebarMenuLabelsResponse(labels={item.menu_key: item.menu_name for item in rows})
