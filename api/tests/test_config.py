from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_REQUIRED = {
    "DATABASE_URL": "postgresql+asyncpg://user:pw@localhost/db",
    "JWT_SECRET": "0123456789abcdef0123456789abcdef0123456789",
}


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    for key, value in {**_REQUIRED, **overrides}.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("http://localhost:5173", ["http://localhost:5173"]),
        (
            "https://a.example.com,https://b.example.com",
            ["https://a.example.com", "https://b.example.com"],
        ),
        (
            " https://a.example.com , https://b.example.com ",
            ["https://a.example.com", "https://b.example.com"],
        ),
        ('["https://a.example.com"]', ["https://a.example.com"]),
    ],
)
def test_cors_origins_accepts_the_forms_a_deployment_writes(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    assert _settings(monkeypatch, CORS_ORIGINS=raw).CORS_ORIGINS == expected


def test_cors_origins_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert _settings(monkeypatch).CORS_ORIGINS == ["http://localhost:5173"]


def test_cors_wildcard_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, CORS_ORIGINS="*")


def test_plaintext_origins_are_refused_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError):
        _settings(
            monkeypatch, ENVIRONMENT="production", CORS_ORIGINS="http://app.example.com"
        )


@pytest.mark.parametrize("secret", ["short", "changeme", "password", "x" * 31])
def test_weak_jwt_secrets_are_refused(
    monkeypatch: pytest.MonkeyPatch, secret: str
) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, JWT_SECRET=secret)
