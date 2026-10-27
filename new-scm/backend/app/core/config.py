"""New SCM settings. Existing asset-manager settings are never imported."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    diagnostics_key: str
    cors_origins: tuple[str, ...]
    log_file: str
    identity_base_url: str = ""
    handoff_key: str = ""
    handoff_origin: str = ""
    frontend_origin: str = ""


def get_settings() -> Settings:
    environment = os.getenv("SCM_ENV", "development").strip().lower()
    if environment not in {"development", "production"}:
        raise ValueError("SCM_ENV must be development or production")
    origins = tuple(
        origin.strip()
        for origin in os.getenv("SCM_CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    if environment == "production" and "*" in origins:
        raise ValueError("Wildcard CORS is forbidden in production")
    return Settings(
        environment=environment,
        database_url=os.getenv("SCM_DATABASE_URL", "").strip(),
        diagnostics_key=os.getenv("SCM_DIAGNOSTICS_KEY", ""),
        cors_origins=origins,
        log_file=os.getenv("SCM_LOG_FILE", ""),
        identity_base_url=os.getenv("SCM_IDENTITY_BASE_URL", "").strip().rstrip("/"),
        handoff_key=os.getenv("SCM_HANDOFF_KEY", ""),
        handoff_origin=os.getenv("SCM_HANDOFF_ORIGIN", "").strip().rstrip("/"),
        frontend_origin=os.getenv("SCM_FRONTEND_ORIGIN", "").strip().rstrip("/"),
    )
