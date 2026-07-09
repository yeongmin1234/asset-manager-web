from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Asset Manager"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://asset_user:change_me@localhost:5432/asset_manager"
    )
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3010,"
        "http://192.168.222.210:3010,"
        "http://112.216.230.162:3010,"
        "http://thelimo.asuscomm.com:3010"
    )
    upload_dir: str = "../uploads"
    install_file_upload_dir: str = "../uploads/install_files"
    install_file_max_size_mb: int = 2048
    export_dir: str = "../exports"
    admin_auth_minutes: int = 60
    admin_reset_code: str = ""
    network_credential_secret_key: str = ""
    scm_reboot_host: str = ""
    scm_reboot_port: int = 22
    scm_reboot_user: str = ""
    scm_reboot_password: str = ""
    scm_mariadb_restart_enabled: bool = False

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
        return list(
            dict.fromkeys(
                origin.strip().rstrip("/")
                for origin in self.cors_origins.split(",")
                if origin.strip()
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
