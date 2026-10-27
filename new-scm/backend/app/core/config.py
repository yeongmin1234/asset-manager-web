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
    )
