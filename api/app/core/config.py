import json
from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32

_WEAK_SECRETS = {"changeme", "secret", "dev", "development", "test", "password"}


class Settings(BaseSettings):
    # enable_decoding=False stops pydantic-settings JSON-decoding complex fields
    # before validation, so the CORS_ORIGINS validator below sees the raw string.
    # CORS_ORIGINS is the only complex field, so nothing else is affected.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", enable_decoding=False
    )

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_TTL_SECONDS: int = 900
    JWT_REFRESH_TTL_SECONDS: int = 60 * 60 * 24 * 7
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    # What Gravatar serves for an address with no uploaded photo. "404" makes the
    # client fall back to initials; "identicon" and friends give every address a
    # distinct generated image. See app.core.avatars.gravatar_url.
    GRAVATAR_DEFAULT_IMAGE: str = "mp"
    # Optional. Without it the profile API still answers, but returns fewer
    # fields, so enrichment degrades rather than breaks.
    GRAVATAR_API_KEY: str = ""
    GRAVATAR_API_TIMEOUT_SECONDS: float = 3.0
    ENVIRONMENT: str = "development"
    DB_POOL_SIZE: int = 5
    PORT: int = 8080
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated list, and treat an empty value as "none".

        Left to itself pydantic-settings parses this field as JSON, so the
        obvious `CORS_ORIGINS=` in an env file is a start-up crash rather than
        the empty list anyone would expect, and a plain comma-separated list is
        a crash too. Both are what a deployment actually writes.
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if text.startswith("["):
            try:
                return json.loads(text)
            except ValueError:
                pass
        return [origin.strip() for origin in text.split(",") if origin.strip()]

    @field_validator("JWT_SECRET")
    @classmethod
    def _secret_must_be_strong(cls, value: str) -> str:
        if len(value) < MIN_JWT_SECRET_LENGTH or value.lower() in _WEAK_SECRETS:
            raise ValueError(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters "
                "of unguessable entropy (e.g. `openssl rand -hex 32`) - it is the "
                "only thing standing between a forged token and hr_admin"
            )
        return value

    @model_validator(mode="after")
    def _cors_must_not_be_wildcard(self) -> Self:
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS must list explicit origins, not '*', because the "
                "API is served with allow_credentials=True"
            )
        if self.is_production:
            insecure = [
                origin
                for origin in self.CORS_ORIGINS
                if origin.startswith("http://")
                and not origin.startswith(("http://localhost", "http://127.0.0.1"))
            ]
            if insecure:
                raise ValueError(
                    f"CORS_ORIGINS contains plaintext origins in production: {insecure}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
