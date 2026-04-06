from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Daily Briefing API"
    api_prefix: str = "/api/v1"
    app_env: str = "prod"
    database_url: str
    auto_create_tables: bool = False

    jwt_secret_key: str = "change-this-secret-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7

    keyword_min_count: int = 1
    keyword_max_count: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
