from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REQUIRED_CORS_ORIGINS = [
    "http://192.168.222.210:3010",
    "http://112.216.230.162:3010",
    "http://thelimo.asuscomm.com:3010",
    "http://localhost:5173",
    "http://localhost:3010",
]


def parse_cors_origins(value: Optional[str]) -> List[str]:
    """Parse a plain comma-separated value without JSON list decoding."""
    if not value:
        return []
    return list(
        dict.fromkeys(
            origin.strip().rstrip("/")
            for origin in value.split(",")
            if origin.strip()
        )
    )


class Settings(BaseSettings):
    app_name: str = "Asset Manager"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://asset_user:change_me@localhost:5432/asset_manager"
    )
    # Keep this as str so pydantic-settings does not require JSON list syntax
    # for the comma-separated CORS_ORIGINS value used by NAS shell env files.
    cors_origins: str = ",".join(REQUIRED_CORS_ORIGINS)
    upload_dir: str = "../uploads"
    attachment_upload_dir: str = "attachments"
    attachment_max_size_mb: int = 20
    install_file_upload_dir: str = "../uploads/install_files"
    install_file_max_size_mb: int = 2048
    export_dir: str = "../exports"
    admin_auth_minutes: int = 60
    admin_reset_code: str = ""
    auth_jwt_secret: str = ""
    auth_token_minutes: int = 480
    trusted_proxy_ips: str = ""
    network_credential_secret_key: str = ""
    scm_reboot_host: str = ""
    scm_reboot_port: int = 22
    scm_reboot_user: str = ""
    scm_reboot_password: str = ""
    scm_mariadb_restart_enabled: bool = False
    ecount_enabled: bool = False
    ecount_company_code: str = ""
    ecount_user_id: str = ""
    ecount_api_cert_key: str = ""
    ecount_api_mode: Literal["test", "production"] = "test"
    ecount_request_timeout: float = 15.0
    ecount_trust_ssl: bool = True
    inventory_scheduler_enabled: bool = False
    inventory_snapshot_max_items: int = 200
    inventory_snapshot_request_interval: float = 1.0
    inventory_snapshot_412_max_retries: int = 2
    inventory_snapshot_retention_days: int = 180
    ai_enabled: bool = False
    ai_provider: str = "openai_compatible"
    ai_model: str = ""
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_timeout_seconds: float = 8.0
    ai_fallback_enabled: bool = True
    ai_min_confidence: float = 0.70

    model_config = SettingsConfigDict(
        # Resolve backend/.env independently of the directory uvicorn was
        # launched from (project root, backend/, systemd, or a NAS script).
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return parse_cors_origins(self.cors_origins)

    @property
    def trusted_proxy_ip_list(self) -> List[str]:
        return [value.strip() for value in self.trusted_proxy_ips.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
