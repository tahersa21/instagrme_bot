from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Instagram Auto Liker"
    debug: bool = False

    data_dir: Path = Path("./data")
    database_url: str = "sqlite:///./data/app.db"

    master_key: str = ""

    admin_username: str = "admin"
    admin_password: str = "change-me"
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    default_likes_per_account: int = 3
    default_min_delay_seconds: int = 30
    default_max_delay_seconds: int = 90
    default_daily_like_limit: int = 100
    default_hourly_like_limit: int = 20
    default_schedule_interval_hours: int = 6

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
