from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Asset Manager"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://asset_user:change_me@localhost:5432/asset_manager"
    )
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3010"]
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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
