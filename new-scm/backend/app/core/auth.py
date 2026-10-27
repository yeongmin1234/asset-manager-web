"""SCM authentication boundary. No identity is trusted until a verifier is wired."""

from dataclasses import dataclass
from typing import Protocol

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class Principal:
    # These fields must come from a server-verified identity and SCM grants.
    subject: str
    name: str
    account_type: str
    status: str
    menu_grants: frozenset[str] = frozenset()
    action_grants: frozenset[str] = frozenset()


class AuthVerifier(Protocol):
    def verify(self, credential: str) -> Principal | None:
        """Return a verified principal, or None for invalid/expired credentials."""


class UnconnectedVerifier:
    def verify(self, credential: str) -> None:
        # No shared secret, identity header, or development bypass is accepted.
        return None


bearer = HTTPBearer(auto_error=False)
verifier: AuthVerifier = UnconnectedVerifier()


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="인증이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    if credentials is None:
        session_token = request.cookies.get("scm_session", "")
        if not session_token:
            raise unauthorized()
        from app.core.handoff import resolve_principal
        from app.core.scm_session import lookup
        identity = lookup(session_token)
        if identity is None:
            raise unauthorized()
        try:
            principal = resolve_principal(*identity)
        except Exception:
            raise unauthorized() from None
        if principal is None:
            raise HTTPException(status_code=403, detail="SCM 접근 권한이 없습니다.")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            from app.core.config import get_settings
            if request.headers.get("origin") != get_settings().frontend_origin:
                raise HTTPException(status_code=403, detail="요청 출처가 올바르지 않습니다.")
        request.state.auth_subject = principal.subject
        return principal
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise unauthorized()
    try:
        principal = verifier.verify(credentials.credentials)
    except Exception:
        # Authentication transport/provider failures must fail closed without details.
        raise unauthorized() from None
    if not isinstance(principal, Principal) or not principal.subject or principal.status != "active":
        raise unauthorized()
    request.state.auth_subject = principal.subject
    return principal
