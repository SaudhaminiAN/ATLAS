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

    market_data_mock_enabled: bool = True
    market_data_mock_timeframe: str = "M15"
    market_data_mock_interval_seconds: float = 2.0
    market_data_outlier_atr_multiplier: float = 5.0
    market_data_outlier_atr_lookback: int = 14
    market_data_gap_tolerance_bars: int = 1

    pipeline_risk_enabled: bool = False

    news_hard_block_minutes_before: int = 15
    news_hard_block_minutes_after: int = 15
    news_soft_downgrade_minutes_before: int = 30
    news_soft_downgrade_minutes_after: int = 30
    news_soft_downgrade_penalty: float = 0.20
    news_calendar_sync_interval_minutes: int = 15
    news_calendar_stale_warning_minutes: int = 60
    news_mock_enabled: bool = True

    market_context_bias_timeframe: str = "H4"
    market_context_primary_timeframe: str = "M15"
    market_context_atr_period: int = 14
    market_context_atr_percentile_lookback: int = 100
    market_context_min_bars_required: int = 100

    mtf_alignment_threshold: float = 0.75
    mtf_bias_source: str = "smc_trend"
    mtf_min_bars: int = 50
    mtf_bar_lookback: int = 120

    technical_swing_lookback: int = 2
    technical_merge_tolerance_pct: float = 0.001
    technical_min_bars: int = 200
    technical_bar_lookback: int = 250

    smc_swing_lookback: int = 2
    smc_displacement_atr_multiplier: float = 1.5
    smc_ob_mitigation_pct: float = 0.50
    smc_equal_level_tolerance_pct: float = 0.001
    smc_fvg_fill_pct: float = 0.50
    smc_min_bars: int = 50
    smc_bar_lookback: int = 120


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
