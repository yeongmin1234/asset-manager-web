import base64
import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.network_credential import (
    NetworkCredential,
    NetworkCredentialCategory,
    NetworkCredentialImportance,
)
from app.schemas.network_credential import (
    NetworkCredentialCreate,
    NetworkCredentialRead,
    NetworkCredentialSummary,
    NetworkCredentialUpdate,
)
from app.services.activity_log_service import record_activity_log


NETWORK_CREDENTIAL_LOG_FIELDS = (
    "category",
    "service_name",
    "internal_url",
    "external_url",
    "port",
    "username",
    "importance",
    "owner",
    "note",
    "is_active",
)


class NetworkCredentialNotFoundError(Exception):
    pass


class NetworkCredentialCryptoConfigError(Exception):
    pass


class NetworkCredentialCryptoError(Exception):
    pass


def get_network_credentials(
    db: Session,
    *,
    keyword: Optional[str] = None,
    category: Optional[NetworkCredentialCategory] = None,
    importance: Optional[NetworkCredentialImportance] = None,
) -> List[NetworkCredential]:
    statement = select(NetworkCredential).where(NetworkCredential.is_active.is_(True))

    if keyword:
        keyword_pattern = "%{}%".format(keyword.strip())
        if keyword_pattern != "%%":
            statement = statement.where(
                or_(
                    NetworkCredential.service_name.ilike(keyword_pattern),
                    NetworkCredential.internal_url.ilike(keyword_pattern),
                    NetworkCredential.external_url.ilike(keyword_pattern),
                    NetworkCredential.username.ilike(keyword_pattern),
                    NetworkCredential.note.ilike(keyword_pattern),
                )
            )

    if category is not None:
        statement = statement.where(NetworkCredential.category == category.value)

    if importance is not None:
        statement = statement.where(NetworkCredential.importance == importance.value)

    statement = statement.order_by(
        NetworkCredential.importance.desc(),
        NetworkCredential.created_at.desc(),
        NetworkCredential.id.desc(),
    )
    return list(db.scalars(statement).all())


def create_network_credential(
    db: Session,
    payload: NetworkCredentialCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> NetworkCredential:
    data = payload.model_dump(exclude={"password"})
    credential = NetworkCredential(
        **_normalize_enum_values(data),
        encrypted_password=encrypt_password(payload.password) if payload.password else None,
    )
    db.add(credential)
    db.flush()
    record_network_credential_activity(
        db,
        action_type="create",
        credential=credential,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="접속정보 등록: {}".format(credential.service_name),
        after_data=serialize_network_credential_activity_data(credential),
    )
    db.commit()
    db.refresh(credential)
    return credential


def get_network_credential(db: Session, credential_id: int) -> NetworkCredential:
    credential = db.scalar(
        select(NetworkCredential).where(
            NetworkCredential.id == credential_id,
            NetworkCredential.is_active.is_(True),
        )
    )
    if credential is None:
        raise NetworkCredentialNotFoundError(
            "Network credential not found: {}".format(credential_id)
        )
    return credential


def update_network_credential(
    db: Session,
    credential_id: int,
    payload: NetworkCredentialUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> NetworkCredential:
    credential = get_network_credential(db, credential_id)
    before_data = serialize_network_credential_activity_data(credential)
    data = _normalize_enum_values(payload.model_dump(exclude={"password"}))

    for field_name, value in data.items():
        setattr(credential, field_name, value)
    if payload.password:
        credential.encrypted_password = encrypt_password(payload.password)

    credential.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_network_credential_activity(
        db,
        action_type="update",
        credential=credential,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="접속정보 수정: {}".format(credential.service_name),
        before_data=before_data,
        after_data=serialize_network_credential_activity_data(credential),
    )
    db.commit()
    db.refresh(credential)
    return credential


def delete_network_credential(
    db: Session,
    credential_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> NetworkCredentialRead:
    credential = get_network_credential(db, credential_id)
    before_data = serialize_network_credential_activity_data(credential)
    deleted_item = to_network_credential_read(credential)
    credential.is_active = False
    credential.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_network_credential_activity(
        db,
        action_type="delete",
        credential=credential,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="접속정보 삭제: {}".format(credential.service_name),
        before_data=before_data,
    )
    db.commit()
    return deleted_item


def reveal_network_credential_password(
    db: Session,
    credential_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    credential = get_network_credential(db, credential_id)
    record_network_credential_access(
        db,
        credential=credential,
        actor_ip=actor_ip,
        user_agent=user_agent,
    )
    db.commit()
    if not credential.encrypted_password:
        return ""
    return decrypt_password(credential.encrypted_password)


def get_network_credential_summary(db: Session) -> NetworkCredentialSummary:
    row = db.execute(
        select(
            func.count(NetworkCredential.id).label("total"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            NetworkCredential.importance
                            == NetworkCredentialImportance.IMPORTANT.value,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("important"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            NetworkCredential.importance
                            == NetworkCredentialImportance.CRITICAL.value,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("critical"),
            func.coalesce(
                func.sum(
                    case(
                        (NetworkCredential.encrypted_password.isnot(None), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("with_password"),
        ).where(NetworkCredential.is_active.is_(True))
    ).one()
    return NetworkCredentialSummary(
        total=int(row.total or 0),
        important=int(row.important or 0),
        critical=int(row.critical or 0),
        with_password=int(row.with_password or 0),
    )


def to_network_credential_read(credential: NetworkCredential) -> NetworkCredentialRead:
    return NetworkCredentialRead(
        id=credential.id,
        category=credential.category,
        service_name=credential.service_name,
        internal_url=credential.internal_url,
        external_url=credential.external_url,
        port=credential.port,
        username=credential.username,
        importance=credential.importance,
        owner=credential.owner,
        note=credential.note,
        is_active=credential.is_active,
        has_password=bool(credential.encrypted_password),
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


def encrypt_password(password: str) -> str:
    try:
        return _get_fernet().encrypt(password.encode("utf-8")).decode("utf-8")
    except NetworkCredentialCryptoConfigError:
        raise
    except Exception as exc:
        raise NetworkCredentialCryptoError("Password encryption failed.") from exc


def decrypt_password(encrypted_password: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
    except NetworkCredentialCryptoConfigError:
        raise
    except Exception as exc:
        raise NetworkCredentialCryptoError("Password decryption failed.") from exc


def _get_fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise NetworkCredentialCryptoConfigError(
            "접속정보 암호화 패키지가 설치되지 않았습니다."
        ) from exc

    secret = getattr(settings, "network_credential_secret_key", None)
    if not secret:
        raise NetworkCredentialCryptoConfigError(
            "접속정보 암호화 키가 설정되지 않았습니다."
        )

    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _normalize_enum_values(data):
    normalized = {}
    for key, value in data.items():
        if hasattr(value, "value"):
            normalized[key] = value.value
        else:
            normalized[key] = value
    return normalized


def serialize_network_credential_activity_data(
    credential: NetworkCredential,
):
    data = {}
    for field_name in NETWORK_CREDENTIAL_LOG_FIELDS:
        data[field_name] = getattr(credential, field_name)
    data["has_password"] = bool(credential.encrypted_password)
    return data


def record_network_credential_activity(
    db: Session,
    *,
    action_type: str,
    credential: NetworkCredential,
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data=None,
    after_data=None,
) -> None:
    record_activity_log(
        db,
        menu_name="접속정보 관리",
        action_type=action_type,
        target_type="network_credential",
        target_id=credential.id,
        target_name=credential.service_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def record_network_credential_access(
    db: Session,
    *,
    credential: NetworkCredential,
    actor_ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    # 1차에서는 기존 변경 이력 테이블에 비밀번호 보기 이벤트만 남긴다.
    # 별도 접근 이력 테이블이 필요하면 이 함수 내부 구현만 교체하면 된다.
    record_network_credential_activity(
        db,
        action_type="reveal-password",
        credential=credential,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="접속정보 비밀번호 보기: {}".format(credential.service_name),
        after_data={"has_password": bool(credential.encrypted_password)},
    )
