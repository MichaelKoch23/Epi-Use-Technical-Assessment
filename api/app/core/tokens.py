from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException
from jose import JWTError, jwt

from app.core.config import settings

_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


def _create_token(
    user_id: uuid.UUID,
    role: str | None,
    token_type: TokenType,
    ttl_seconds: int,
    jti: uuid.UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    if role is not None:
        payload["role"] = role
    if jti is not None:
        payload["jti"] = str(jti)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(user_id, role, "access", settings.JWT_ACCESS_TTL_SECONDS)


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.JWT_REFRESH_TTL_SECONDS)


def create_refresh_token(user_id: uuid.UUID, jti: uuid.UUID) -> str:
    return _create_token(
        user_id, None, "refresh", settings.JWT_REFRESH_TTL_SECONDS, jti=jti
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload
