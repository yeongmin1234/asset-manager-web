import hashlib
import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

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
