"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ATLAS"
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = Field(
        default="postgresql+asyncpg://atlas:atlas@localhost:5432/atlas",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    jwt_secret: str = Field(min_length=16)
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    pipeline_risk_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
