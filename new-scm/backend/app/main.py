"""Independent new SCM system API. No business writes in stage 3."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import monotonic
from secrets import compare_digest

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
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
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["X-SCM-Diagnostics-Key"],
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
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%d",
        request.method,
        request.url.path,
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
