"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API Keys
    fred_api_key: SecretStr | None = None
    reddit_client_id: SecretStr | None = None
    reddit_client_secret: SecretStr | None = None
    reddit_user_agent: str = "MarketView/1.0"

    # Database
    database_url: str = "postgresql+asyncpg://marketview:marketview@localhost:5432/marketview"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Report Settings
    default_report_level: int = 2
    report_output_dir: str = "./reports"

    # Cache TTL (seconds)
    cache_ttl_fred: int = 3600  # 1 hour
    cache_ttl_reddit: int = 900  # 15 minutes
    cache_ttl_crypto: int = 300  # 5 minutes
    cache_ttl_equity: int = 900  # 15 minutes

    # Rate Limits (requests per minute)
    rate_limit_fred: int = 120
    rate_limit_reddit: int = 60
    rate_limit_coingecko: int = 30
    rate_limit_yahoo: int = 33  # 2000/hr = ~33/min

    @field_validator("default_report_level")
    @classmethod
    def validate_report_level(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError("Report level must be 1, 2, or 3")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
