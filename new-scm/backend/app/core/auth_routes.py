"""Same-origin independent login. Neither bearer JWT nor handoff is issued."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from app.core import local_auth
from app.core.auth import Principal
from app.core.config import get_settings
from app.core.permissions import require_permission

router = APIRouter(prefix="/api/v1")


def origin_check(request: Request):
    settings = get_settings()
    origin = settings.frontend_origin
    # HTTP is permitted only on loopback development/tunnel origins.
    from urllib.parse import urlsplit
    parsed = urlsplit(origin)
    valid = (parsed.scheme in {"http", "https"} and parsed.hostname
             and not (parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment)
             and (parsed.scheme == "https" or (settings.environment == "development"
                  and parsed.hostname in {"127.0.0.1", "localhost"})))
    if not valid or request.headers.get("origin") != origin:
        raise HTTPException(status_code=403, detail="origin_rejected")


def run(operation):
    try:
        return operation()
    except local_auth.AuthFailure as exc:
        headers = {"Cache-Control": "no-store"}
        if exc.status == 429:
            headers["Retry-After"] = str(local_auth.WINDOW_SECONDS)
        return JSONResponse({"ok": False, "data": None,
                             "error": {"code": exc.code, "message": "인증 요청을 처리할 수 없습니다."}},
                            status_code=exc.status, headers=headers)
    except Exception:
        local_auth.logger.error("auth_storage_unavailable")
        return JSONResponse({"ok": False, "data": None,
                             "error": {"code": "auth_unavailable", "message": "인증 서비스를 확인해주세요."}},
                            status_code=503, headers={"Cache-Control": "no-store"})


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login", dependencies=[Depends(origin_check)])
def login(payload: LoginBody, request: Request, response: Response):
    def operation():
        # Do not trust forwarded headers supplied by clients. Shared proxy buckets
        # deliberately remain conservative until a trusted proxy policy is approved.
        peer = request.client.host if request.client else "unknown"
        token = local_auth.login(payload.username, payload.password, peer,
                                 request.cookies.get("scm_session", ""))
        response.set_cookie("scm_session", token, max_age=local_auth.SESSION_SECONDS,
                            httponly=True, secure=get_settings().environment == "production",
                            samesite="strict", path="/api/v1")
        response.headers["Cache-Control"] = "no-store"
        return {"ok": True, "data": {"authenticated": True}, "error": None}
    return run(operation)


@router.post("/auth/logout", dependencies=[Depends(origin_check)])
def logout(request: Request, response: Response):
    def operation():
        local_auth.logout(request.cookies.get("scm_session", ""))
        response.delete_cookie("scm_session", path="/api/v1", httponly=True,
                               secure=get_settings().environment == "production", samesite="strict")
        response.headers["Cache-Control"] = "no-store"
        return {"ok": True, "data": {"logged_out": True}, "error": None}
    return run(operation)


@router.get("/admin/auth/users")
def users(response: Response, _principal=Depends(require_permission(admin=True))):
    response.headers["Cache-Control"] = "no-store"
    return run(lambda: {"ok": True, "data": {"users": local_auth.list_users()}, "error": None})


class CredentialsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str | None = Field(default=None, min_length=12, max_length=256)
    enabled: bool


@router.post("/admin/auth/users/{user_id}/credentials", dependencies=[Depends(origin_check)])
def credentials(user_id: int, payload: CredentialsBody,
                principal: Principal = Depends(require_permission(admin=True))):
    if str(user_id) == principal.subject:
        raise HTTPException(status_code=409, detail="self_credential_change_requires_cli")
    def operation():
        local_auth.set_credentials(user_id, payload.password, payload.enabled)
        return {"ok": True, "data": {"updated": True, "sessions_revoked": True}, "error": None}
    return run(operation)
