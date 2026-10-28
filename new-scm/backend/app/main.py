"""Independent SCM authentication API; business APIs remain gated placeholders."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import monotonic
from secrets import compare_digest

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.auth import Principal
from app.core.permissions import require_permission
from app.core.auth_routes import router as auth_router
from app.db.database import DatabaseUnavailable, probe_database

settings = get_settings()
logger = logging.getLogger("new_scm")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

app = FastAPI(
    title="New SCM API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.environment == "development" else None,
)
browser_origins = tuple(dict.fromkeys((*settings.cors_origins, settings.frontend_origin)))
browser_origins = tuple(origin for origin in browser_origins if origin and origin != "*")
if browser_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(browser_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-SCM-Diagnostics-Key"],
    )


def success(data: dict) -> dict:
    return {"ok": True, "data": data, "error": None}


def failure(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "data": None, "error": {"code": code, "message": message}},
    )


@app.middleware("http")
async def request_log(request: Request, call_next):
    start = monotonic()
    response = await call_next(request)
    if request.url.path.startswith(("/api/v1/auth/", "/api/v1/admin/auth/")):
        response.headers["Cache-Control"] = "no-store"
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%d",
        request.method,
        request.scope.get("route").path if request.scope.get("route") else "unmatched",
        response.status_code,
        int((monotonic() - start) * 1000),
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    return failure("http_error", "요청을 처리할 수 없습니다.", exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError):
    return failure("validation_error", "요청 형식이 올바르지 않습니다.", 422)


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, _exc: Exception):
    logger.error("unhandled_request_error")
    return failure("internal_error", "요청을 처리할 수 없습니다.", 500)


@app.get("/health")
def health():
    return success({"service": "new-scm", "status": "up"})


@app.get("/api/v1/system/status")
def system_status():
    return success({"service": "new-scm", "status": "ready", "database": "not_checked"})


@app.get("/api/v1/auth/me")
def auth_me(response: Response, principal: Principal = Depends(require_permission())):
    response.headers["Cache-Control"] = "no-store"
    return success({
        "subject": principal.subject,
        "name": principal.name,
        "account_type": principal.account_type,
        "status": principal.status,
        "menu_grants": sorted(principal.menu_grants),
        "action_grants": sorted(principal.action_grants),
    })


app.include_router(auth_router)


@app.get("/api/v1/system/db-status")
def database_status(x_scm_diagnostics_key: str | None = Header(default=None)):
    if not settings.diagnostics_key or not x_scm_diagnostics_key or not compare_digest(
        x_scm_diagnostics_key, settings.diagnostics_key
    ):
        return failure("forbidden", "접근할 수 없습니다.", 403)
    try:
        result = probe_database()
    except DatabaseUnavailable as exc:
        logger.warning("database_probe_unavailable code=%s", str(exc))
        return failure("database_unavailable", "DB 상태를 확인할 수 없습니다.", 503)
    return success(result)


@app.api_route("/api/v1/{unimplemented_path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
def unimplemented_api(
    unimplemented_path: str,
    _principal: Principal = Depends(require_permission()),
):
    # Stage 4-1 business APIs do not exist yet. Never expose them anonymously.
    return failure("not_found", "요청한 API가 없습니다.", 404)
