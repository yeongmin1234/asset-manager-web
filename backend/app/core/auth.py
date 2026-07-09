from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(user: User) -> str:
    secret = _get_jwt_secret()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=max(1, int(settings.auth_token_minutes)))
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        payload = jwt.decode(
            credentials.credentials,
            _get_jwt_secret(),
            algorithms=["HS256"],
        )
        user_id = int(payload.get("sub", ""))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def require_authenticated_access(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    if user.role == "admin" or request.method.upper() in SAFE_METHODS:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="관리자 권한이 필요합니다.",
    )


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다.",
        )
    return user


def require_menu_permission(*permissions: str):
    required_permissions: Tuple[str, ...] = tuple(permissions)

    def dependency(
        request: Request,
        user: User = Depends(get_current_user),
    ) -> User:
        if user.role == "admin":
            return user
        user_permissions = set(user.menu_permissions or [])
        if not user_permissions.intersection(required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 메뉴에 접근할 권한이 없습니다.",
            )
        if request.method.upper() not in SAFE_METHODS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자만 데이터를 변경할 수 있습니다.",
            )
        return user

    return dependency


def _get_jwt_secret() -> str:
    secret = (settings.auth_jwt_secret or "").strip()
    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH_JWT_SECRET 설정이 필요합니다.",
        )
    return secret


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
