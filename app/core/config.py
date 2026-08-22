"""Environment-backed application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional `.env` file."""

    database_url: str = "sqlite:///./food_trucks.db"
    log_level: str = "INFO"
    default_radius_km: float = 5.0
    food_truck_data_url: str = "https://data.sfgov.org/resource/rqzj-sfat.json?$limit=50000"
    food_truck_request_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
