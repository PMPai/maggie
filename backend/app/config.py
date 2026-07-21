from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET: str = "change-me"
    DATABASE_URL: str = "postgresql+asyncpg://maggie:maggie@postgres:5432/maggie"
    SYNC_DATABASE_URL: str = "postgresql://maggie:maggie@postgres:5432/maggie"
    REDIS_URL: str = "redis://redis:6379/0"
    FILE_STORAGE_ROOT: str = "/data/archive"
    MAX_UPLOAD_SIZE_MB: int = 100
    DEFAULT_TIMEZONE: str = "Asia/Taipei"
    DEFAULT_CURRENCY: str = "TWD"
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "openai-compatible"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_MODEL: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
