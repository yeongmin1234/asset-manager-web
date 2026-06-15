from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Asset Manager"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://asset_user:change_me@localhost:5432/asset_manager"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3010"]
    upload_dir: str = "../uploads"
    export_dir: str = "../exports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
