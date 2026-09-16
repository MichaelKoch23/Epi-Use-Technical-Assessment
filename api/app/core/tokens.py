"""JWT access/refresh tokens (§9.1): HS256, signed with `JWT_SECRET`.
Short-lived access tokens carry the role (so a resource server never has
to look the user up just to authorise a read); refresh tokens don't, so a
role change takes effect the moment the access token it minted expires."""

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
    """The `expires_at` to record alongside a refresh token's `jti`, so the
    stored row and the token itself cannot disagree about its lifetime."""
    return datetime.now(UTC) + timedelta(seconds=settings.JWT_REFRESH_TTL_SECONDS)


def create_refresh_token(user_id: uuid.UUID, jti: uuid.UUID) -> str:
    """Refresh tokens carry a `jti` naming the `refresh_token` row that
    records whether they are still live. Access tokens deliberately do not:
    they last fifteen minutes and are verified statelessly, which is the
    whole reason the pair is split this way."""
    return _create_token(
        user_id, None, "refresh", settings.JWT_REFRESH_TTL_SECONDS, jti=jti
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Raises `HTTPException(401)` on a bad signature, expiry, or the
    wrong token `type` - a refresh token can't be replayed as an access
    token, and vice versa."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload
