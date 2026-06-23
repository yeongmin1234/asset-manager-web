from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.network_credential import (
    NetworkCredentialCategory,
    NetworkCredentialImportance,
)
from app.schemas.network_credential import (
    NetworkCredentialCreate,
    NetworkCredentialRead,
    NetworkCredentialRevealRequest,
    NetworkCredentialRevealResponse,
    NetworkCredentialSummary,
    NetworkCredentialUpdate,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.network_credential_service import (
    NetworkCredentialCryptoConfigError,
    NetworkCredentialCryptoError,
    NetworkCredentialNotFoundError,
    create_network_credential,
    delete_network_credential,
    get_network_credential,
    get_network_credential_summary,
    get_network_credentials,
    reveal_network_credential_password,
    to_network_credential_read,
    update_network_credential,
)


router = APIRouter(prefix="/network-credentials", tags=["network-credentials"])


@router.get("", response_model=List[NetworkCredentialRead])
def list_network_credentials(
    keyword: Optional[str] = None,
    category: Optional[NetworkCredentialCategory] = Query(default=None),
    importance: Optional[NetworkCredentialImportance] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[NetworkCredentialRead]:
    try:
        credentials = get_network_credentials(
            db,
            keyword=keyword,
            category=category,
            importance=importance,
        )
        return [to_network_credential_read(credential) for credential in credentials]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/summary", response_model=NetworkCredentialSummary)
def read_network_credential_summary(
    db: Session = Depends(get_db),
) -> NetworkCredentialSummary:
    try:
        return get_network_credential_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보 요약을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/{credential_id}", response_model=NetworkCredentialRead)
def read_network_credential(
    credential_id: int,
    db: Session = Depends(get_db),
) -> NetworkCredentialRead:
    try:
        return to_network_credential_read(get_network_credential(db, credential_id))
    except NetworkCredentialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="접속정보를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보를 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=NetworkCredentialRead, status_code=status.HTTP_201_CREATED)
def create_new_network_credential(
    request: Request,
    payload: NetworkCredentialCreate,
    db: Session = Depends(get_db),
) -> NetworkCredentialRead:
    try:
        credential = create_network_credential(
            db,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return to_network_credential_read(credential)
    except NetworkCredentialCryptoConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보 암호화 설정이 필요합니다.",
        ) from exc
    except NetworkCredentialCryptoError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호를 안전하게 저장하지 못했습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{credential_id}", response_model=NetworkCredentialRead)
def update_existing_network_credential(
    request: Request,
    credential_id: int,
    payload: NetworkCredentialUpdate,
    db: Session = Depends(get_db),
) -> NetworkCredentialRead:
    try:
        credential = update_network_credential(
            db,
            credential_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return to_network_credential_read(credential)
    except NetworkCredentialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="접속정보를 찾을 수 없습니다.",
        ) from exc
    except NetworkCredentialCryptoConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보 암호화 설정이 필요합니다.",
        ) from exc
    except NetworkCredentialCryptoError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호를 안전하게 저장하지 못했습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보를 수정하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.delete("/{credential_id}", response_model=NetworkCredentialRead)
def delete_existing_network_credential(
    request: Request,
    credential_id: int,
    db: Session = Depends(get_db),
) -> NetworkCredentialRead:
    try:
        return delete_network_credential(
            db,
            credential_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except NetworkCredentialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="접속정보를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보를 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("/{credential_id}/reveal-password", response_model=NetworkCredentialRevealResponse)
def reveal_existing_network_credential_password(
    request: Request,
    credential_id: int,
    payload: NetworkCredentialRevealRequest,
    db: Session = Depends(get_db),
) -> NetworkCredentialRevealResponse:
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

    try:
        password = reveal_network_credential_password(
            db,
            credential_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return NetworkCredentialRevealResponse(
            password=password,
            expires_in=15,
            message=None if password else "등록된 비밀번호가 없습니다.",
        )
    except NetworkCredentialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="접속정보를 찾을 수 없습니다.",
        ) from exc
    except NetworkCredentialCryptoConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속정보 암호화 설정이 필요합니다.",
        ) from exc
    except NetworkCredentialCryptoError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호를 안전하게 확인하지 못했습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="비밀번호 확인 중 DB 연결에 실패했습니다.",
        ) from exc
