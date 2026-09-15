from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_TTL_SECONDS: int = 900
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    GRAVATAR_DEFAULT_IMAGE: str = "mp"
    ENVIRONMENT: str = "development"
    DB_POOL_SIZE: int = 5
    PORT: int = 8080


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
