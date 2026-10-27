"""Separate SCM system, menu, and API action grants; deny by default."""

from fastapi import Depends, HTTPException

from app.core.auth import Principal, get_current_principal


SYSTEM_ACCESS = "system.access"


def enforce_permission(
    principal: Principal,
    *,
    menu: str | None = None,
    action: str | tuple[str, ...] | None = None,
    admin: bool = False,
) -> Principal:
    if principal.status != "active" or SYSTEM_ACCESS not in principal.action_grants:
        raise HTTPException(status_code=403, detail="SCM 접근 권한이 없습니다.")
    if menu is not None and menu not in principal.menu_grants:
        raise HTTPException(status_code=403, detail="메뉴 접근 권한이 없습니다.")
    required_actions = (action,) if isinstance(action, str) else (action or ())
    if any(required not in principal.action_grants for required in required_actions):
        raise HTTPException(status_code=403, detail="작업 권한이 없습니다.")
    if admin and (principal.account_type != "admin" or "admin.manage" not in principal.action_grants):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")
    return principal


def require_permission(*, menu: str | None = None, action: str | tuple[str, ...] | None = None, admin: bool = False):
    """Attach to each future business route; menu and action checks are independent."""

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        return enforce_permission(principal, menu=menu, action=action, admin=admin)

    return dependency
