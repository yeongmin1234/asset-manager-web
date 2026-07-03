import hashlib
import hmac
import base64
import calendar
import json
import secrets
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.admin_setting import AdminSetting


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 200000
MIN_ADMIN_PASSWORD_LENGTH = 6


class AdminPasswordTooShortError(Exception):
    pass


class AdminPasswordRequiredError(Exception):
    pass


class AdminPasswordInvalidError(Exception):
    pass


class AdminResetCodeNotConfiguredError(Exception):
    pass


class AdminAuthTokenInvalidError(Exception):
    pass


def is_admin_password_configured(db: Session) -> bool:
    setting = get_admin_setting(db)
    return bool(setting and setting.password_hash)


def set_admin_password(
    db: Session,
    new_password: str,
    current_password: Optional[str] = None,
) -> AdminSetting:
    if len(new_password or "") < MIN_ADMIN_PASSWORD_LENGTH:
        raise AdminPasswordTooShortError()

    setting = get_or_create_admin_setting(db)
    if setting.password_hash:
        if not current_password:
            raise AdminPasswordRequiredError()
        if not verify_password(current_password, setting.password_hash):
            raise AdminPasswordInvalidError()

    setting.password_hash = hash_password(new_password)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def verify_admin_password(db: Session, password: str) -> bool:
    setting = get_admin_setting(db)
    if not setting or not setting.password_hash:
        return False
    return verify_password(password, setting.password_hash)


def create_admin_auth_token(db: Session, expires_at: datetime) -> str:
    setting = get_admin_setting(db)
    if not setting or not setting.password_hash:
        raise AdminAuthTokenInvalidError()

    payload = {
        "exp": int(calendar.timegm(expires_at.utctimetuple())),
        "nonce": secrets.token_urlsafe(16),
    }
    payload_text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_token = base64.urlsafe_b64encode(payload_text.encode("utf-8")).decode("utf-8").rstrip("=")
    signature = _sign_admin_token_payload(payload_token, setting.password_hash)
    return "{}.{}".format(payload_token, signature)


def verify_admin_auth_token(db: Session, token: str) -> bool:
    setting = get_admin_setting(db)
    if not setting or not setting.password_hash or not token:
        return False

    try:
        payload_token, signature = str(token).split(".", 1)
        expected_signature = _sign_admin_token_payload(payload_token, setting.password_hash)
        if not hmac.compare_digest(signature, expected_signature):
            return False
        padded_payload = payload_token + "=" * (-len(payload_token) % 4)
        payload_text = base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_text)
        expires_at = int(payload.get("exp") or 0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False

    return expires_at > int(time.time())


def reset_admin_password_with_reset_code(
    db: Session,
    new_password: str,
) -> AdminSetting:
    if len(new_password or "") < MIN_ADMIN_PASSWORD_LENGTH:
        raise AdminPasswordTooShortError()

    setting = get_or_create_admin_setting(db)
    setting.password_hash = hash_password(new_password)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def is_admin_reset_code_configured() -> bool:
    return bool(str(settings.admin_reset_code or "").strip())


def verify_admin_reset_code(reset_code: str) -> bool:
    expected_code = str(settings.admin_reset_code or "").strip()
    if not expected_code:
        raise AdminResetCodeNotConfiguredError()
    return hmac.compare_digest(str(reset_code or ""), expected_code)


def get_admin_setting(db: Session) -> Optional[AdminSetting]:
    return db.scalar(select(AdminSetting).order_by(AdminSetting.id.asc()).limit(1))


def get_or_create_admin_setting(db: Session) -> AdminSetting:
    setting = get_admin_setting(db)
    if setting is not None:
        return setting

    setting = AdminSetting()
    db.add(setting)
    db.flush()
    return setting


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return "{}${}${}${}".format(
        PASSWORD_HASH_ALGORITHM,
        PASSWORD_HASH_ITERATIONS,
        salt,
        password_hash,
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_hash = stored_hash.split("$", 3)
        iterations = int(iterations_text)
    except (AttributeError, ValueError):
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return secrets.compare_digest(actual_hash, expected_hash)


def _sign_admin_token_payload(payload_token: str, password_hash: str) -> str:
    signature = hmac.new(
        password_hash.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature
