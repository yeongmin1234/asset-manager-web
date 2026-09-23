"""Short-lived, narrowly scoped native downloads; no bearer tokens in URLs."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import _get_jwt_secret, get_current_user
from app.db.database import get_db
from app.services import attachment_service as attachments
from app.services import install_file_service as installs

logger = logging.getLogger("app.downloads")
router = APIRouter(prefix="/downloads", tags=["downloads"])
EXPORTS = {
    "/assets/export/excel": "assets",
    "/assets/import/template": "assets",
    "/hr/accounts/import/template": "hr_list",
    "/admin/audit-logs/export": "admin",
}
FILE_PATH = re.compile(r"^/(install-files|attachments)/(\d+)/(download|preview)$")


def is_download_path(path):
    match = FILE_PATH.fullmatch(path)
    return path in EXPORTS or bool(match and (match[1] == "attachments" or match[3] == "download"))


def disposition(filename, kind="attachment"):
    cleaned = str(filename).replace("\r", "").replace("\n", "").replace("/", "_").replace("\\", "_")
    fallback = re.sub(r'[^A-Za-z0-9._ ()-]', "_", cleaned) or "download"
    return '{}; filename="{}"; filename*=UTF-8\'\'{}'.format(kind, fallback, quote(cleaned, safe=""))


def check_target(path, db, user, state):
    if not is_download_path(path):
        raise HTTPException(400, "지원하지 않는 다운로드 경로입니다.")
    match = FILE_PATH.fullmatch(path)
    permission = EXPORTS.get(path, "admin" if match and match[1] == "install-files" else None)
    if user.role != "admin" and permission and (permission == "admin" or permission not in set(user.menu_permissions or [])):
        raise HTTPException(403, "다운로드 권한이 없습니다.")
    if not match:
        return
    state["download_file_id"] = int(match[2])
    try:
        if match[1] == "install-files":
            item = installs.get_install_file(db, int(match[2]))
            state["download_filename"] = item.original_filename
            path_on_disk = installs.resolve_install_file_path(item)
        else:
            item = attachments.get_attachment(db, int(match[2]))
            attachments.ensure_attachment_access(user, item.entity_type)
            state["download_filename"] = item.original_filename
            if match[3] == "preview" and not attachments.can_preview_attachment(item):
                raise HTTPException(400, "미리보기는 이미지와 PDF만 지원합니다.")
            path_on_disk = attachments.resolve_attachment_path(item)
        if not path_on_disk.is_file():
            raise HTTPException(404, "파일 원본을 찾을 수 없습니다.")
        # Check readability before sending response headers.
        with path_on_disk.open("rb"):
            pass
    except (installs.InstallFileNotFoundError, attachments.AttachmentNotFoundError) as exc:
        raise HTTPException(404, "파일을 찾을 수 없습니다.") from exc
    except (installs.InstallFileValidationError, attachments.AttachmentValidationError) as exc:
        raise HTTPException(403, "파일 경로에 접근할 수 없습니다.") from exc
    except OSError as exc:
        raise HTTPException(500, "서버에서 파일을 읽을 수 없습니다.") from exc


@router.get("/prepare")
def prepare_download(request: Request, response: Response, path: str, query: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    request.scope["state"]["download_api"] = path
    check_target(path, db, user, request.scope["state"])
    if len(query) > 8192:
        raise HTTPException(400, "다운로드 조건이 너무 깁니다.")
    now = datetime.now(timezone.utc)
    download_id = uuid4().hex
    expires = now + timedelta(seconds=90)
    session_expiry = request.scope["state"].get("auth_expires_at")
    if session_expiry is not None:
        expires = min(expires, datetime.fromtimestamp(session_expiry, timezone.utc))
    ticket = jwt.encode({"sub": str(user.id), "aud": "native-download", "jti": download_id, "path": path,
                         "query": query, "iat": now, "exp": expires},
                        _get_jwt_secret(), algorithm="HS256")
    response.headers["Cache-Control"] = "no-store"
    return {"ticket": ticket, "download_id": download_id}


class DownloadMiddleware:
    """POST handoff reuses existing GET routes and all their permission checks.

    Transfer credentials never enter request URLs or access logs. No file body
    buffering: send passes each ASGI chunk straight to the server.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        native = scope["path"] == "/downloads/transfer"
        monitored = native or scope["path"] == "/downloads/prepare" or is_download_path(scope["path"])
        if not monitored:
            return await self.app(scope, receive, send)
        state = scope.setdefault("state", {})
        state["download_started_at"] = datetime.now(timezone.utc).isoformat()
        api_path = scope["path"]
        if api_path == "/downloads/prepare":
            candidate = parse_qs(scope.get("query_string", b"").decode("utf-8", errors="replace")).get("path", [""])[0]
            if is_download_path(candidate):
                api_path = candidate
        state["download_api"] = api_path
        status_code = 500
        started = False
        suppress_body = False

        async def error_response(status, detail):
            payload = json.dumps({
                "type": "asset-manager-download-error",
                "downloadId": state.get("download_id"),
                "message": detail,
                "status": status,
            }, ensure_ascii=False).replace("<", "\\u003c")
            await HTMLResponse('<!doctype html><meta charset="utf-8"><script>window.parent.postMessage({}, "*");</script>'.format(payload), status_code=status,
                               headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})(scope, receive, send)

        async def tracked_send(message):
            nonlocal status_code, started, suppress_body
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if status_code >= 400 and native:
                    suppress_body = True
                    started = True
                    reasons = {401: "로그인이 만료되었습니다. 다시 로그인해 주세요.", 403: "다운로드 권한이 없습니다.", 404: "파일을 찾을 수 없습니다."}
                    await error_response(status_code, reasons.get(status_code, "파일 전송을 시작하지 못했습니다 (HTTP {}).".format(status_code)))
                    return
                started = True
                headers = list(message.get("headers", []))
                for key, value in headers:
                    if key.lower() == b"content-disposition":
                        state.setdefault("download_filename", value.decode("latin-1"))
                if native:
                    headers += [(b"cache-control", b"no-store"), (b"referrer-policy", b"no-referrer")]
                message = {**message, "headers": headers}
            if not suppress_body:
                await send(message)

        try:
            if native:
                if scope["method"] != "POST":
                    raise HTTPException(405, "POST 요청이 필요합니다.")
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        raise HTTPException(400, "연결이 끊어졌습니다.")
                    body.extend(message.get("body", b""))
                    if len(body) > 16384:
                        raise HTTPException(413, "잘못된 다운로드 요청입니다.")
                    if not message.get("more_body"):
                        break
                form = parse_qs(body.decode("ascii", errors="replace"))
                submitted_download_id = form.get("download_id", [""])[0]
                if re.fullmatch(r"[a-f0-9]{32}", submitted_download_id):
                    state["download_id"] = submitted_download_id
                try:
                    token = form.get("ticket", [""])[0]
                    payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"], audience="native-download",
                                         options={"require": ["sub", "exp", "iat", "jti", "path", "query"]})
                    if not is_download_path(payload["path"]) or payload["jti"] != submitted_download_id:
                        raise ValueError("invalid target")
                    state["download_id"] = payload["jti"]
                    state["native_download_user_id"] = int(payload["sub"])
                except (jwt.PyJWTError, ValueError, KeyError, TypeError):
                    raise HTTPException(401, "다운로드 요청이 만료되었습니다. 다시 시도해 주세요.")
                scope = {**scope, "method": "GET", "path": payload["path"], "raw_path": payload["path"].encode(),
                         "query_string": payload["query"].encode("utf-8")}
                scope["headers"] = [(k, v) for k, v in scope["headers"] if k.lower() not in (b"content-length", b"content-type", b"authorization")]
            if native:
                state["download_api"] = scope["path"]
            await self.app(scope, receive, tracked_send)
            if status_code >= 400:
                reasons = {400: "invalid_request", 401: "authentication_required_or_expired", 403: "permission_denied",
                           404: "file_or_resource_not_found", 422: "invalid_parameters", 500: "server_error", 503: "service_unavailable"}
                self.log(scope, status_code, reasons.get(status_code, "http_error"))
        except Exception as exc:
            status_code = exc.status_code if isinstance(exc, HTTPException) else (404 if isinstance(exc, FileNotFoundError) else 500)
            self.log(scope, status_code, type(exc).__name__)
            if started:
                raise  # Preserve interrupted transfer; never claim a truncated file succeeded.
            if native:
                await error_response(status_code, exc.detail if isinstance(exc, HTTPException) else "파일 전송 중 서버 오류가 발생했습니다.")
            else:
                await JSONResponse({"detail": "파일을 찾을 수 없습니다." if status_code == 404 else "다운로드 중 서버 오류가 발생했습니다."}, status_code=status_code)(scope, receive, send)

    @staticmethod
    def log(scope, status, reason):
        state = scope.get("state", {})
        match = FILE_PATH.fullmatch(state.get("download_api", ""))
        logger.error("download_failed %s", json.dumps({
            "user_id": state.get("download_user_id", state.get("native_download_user_id")),
            "file_id": state.get("download_file_id", match[2] if match else None),
            "filename": state.get("download_filename"), "request_time": state.get("download_started_at"),
            "api": state.get("download_api", scope["path"]), "http_status": status, "reason": reason,
        }, ensure_ascii=False))
