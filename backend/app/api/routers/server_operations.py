from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.server_operation import (
    ScmMariaDbRestartRequest,
    ScmMariaDbRestartResponse,
    ScmMariaDbRestartDryRunRequest,
    ScmMariaDbRestartDryRunResponse,
    ScmStatusResponse,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.server_operation_service import (
    MARIADB_DRY_RUN_SUCCESS_MESSAGE,
    execute_scm_mariadb_restart,
    get_scm_status,
    is_scm_mariadb_restart_enabled,
    validate_scm_mariadb_restart_dry_run,
)


router = APIRouter(prefix="/server-operations", tags=["server-operations"])


@router.get("/scm/status", response_model=ScmStatusResponse)
def read_scm_status() -> ScmStatusResponse:
    return get_scm_status()


@router.post("/scm/mariadb/restart/dry-run", response_model=ScmMariaDbRestartDryRunResponse)
def dry_run_scm_mariadb_restart(
    payload: ScmMariaDbRestartDryRunRequest,
    db: Session = Depends(get_db),
) -> ScmMariaDbRestartDryRunResponse:
    try:
        validate_scm_mariadb_restart_dry_run(payload.reason, payload.confirm_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not is_admin_password_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )
    if not verify_admin_password(db, payload.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 비밀번호가 올바르지 않습니다.",
        )

    return ScmMariaDbRestartDryRunResponse(
        ok=True,
        message=MARIADB_DRY_RUN_SUCCESS_MESSAGE,
        dry_run=True,
    )


@router.post("/scm/mariadb/restart", response_model=ScmMariaDbRestartResponse)
def restart_scm_mariadb(
    payload: ScmMariaDbRestartRequest,
    db: Session = Depends(get_db),
) -> ScmMariaDbRestartResponse:
    if not is_scm_mariadb_restart_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="현재 실제 MariaDB 재시작은 비활성화되어 있습니다.",
        )

    try:
        validate_scm_mariadb_restart_dry_run(payload.reason, payload.confirm_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not is_admin_password_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )
    if not verify_admin_password(db, payload.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 비밀번호가 올바르지 않습니다.",
        )

    # TODO: activity log 연동 시 action_type=scm-mariadb-restart, reason만 저장하고 비밀번호/SSH 정보는 저장하지 않습니다.
    try:
        result = execute_scm_mariadb_restart()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ScmMariaDbRestartResponse(**result)
