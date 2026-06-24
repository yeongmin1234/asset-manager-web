from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.server_operation import (
    ScmRebootDryRunRequest,
    ScmRebootDryRunResponse,
    ScmStatusResponse,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.server_operation_service import (
    get_scm_status,
    validate_scm_reboot_dry_run,
)


router = APIRouter(prefix="/server-operations", tags=["server-operations"])


@router.get("/scm/status", response_model=ScmStatusResponse)
def read_scm_status() -> ScmStatusResponse:
    return get_scm_status()


@router.post("/scm/reboot/dry-run", response_model=ScmRebootDryRunResponse)
def dry_run_scm_reboot(
    payload: ScmRebootDryRunRequest,
    db: Session = Depends(get_db),
) -> ScmRebootDryRunResponse:
    try:
        validate_scm_reboot_dry_run(payload.reason, payload.confirm_text)
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

    return ScmRebootDryRunResponse(
        ok=True,
        message="재부팅 실행 조건이 확인되었습니다. 실제 재부팅은 3단계에서 활성화됩니다.",
        dry_run=True,
    )
