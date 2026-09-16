"""`/api/v1/auth/*` — §9.1: email/password login with Argon2id, short-lived
access tokens and rotating refresh tokens."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.passwords import hash_password, verify_password
from app.core.rate_limit import login_rate_limiter
from app.core.security import Principal, get_current_principal
from app.core.tokens import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.app_user import AppUser
from app.schemas.auth import LoginRequest, MeResponse, RefreshRequest, TokenPair

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Verified on every login attempt, even one against an email that doesn't
# exist, so a nonexistent-email response takes the same time as a
# wrong-password one — the account-enumeration timing side channel this
# closes is exactly what a naive `if user is None: raise` would open.
_DUMMY_HASH = hash_password("not-a-real-password")


async def _user_by_id(session: AsyncSession, user_id: uuid.UUID) -> AppUser | None:
    return (
        await session.execute(select(AppUser).where(AppUser.id == user_id))
    ).scalar_one_or_none()


@router.post(
    "/login", response_model=TokenPair, dependencies=[Depends(login_rate_limiter)]
)
async def login(
    body: LoginRequest, session: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = (
        await session.execute(select(AppUser).where(AppUser.email == body.email))
    ).scalar_one_or_none()
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(body.password, password_hash)

    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest, session: AsyncSession = Depends(get_db)
) -> TokenPair:
    payload = decode_token(body.refresh_token, expected_type="refresh")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc

    user = await _user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")

    # Rotation: a stolen refresh token that's already been used once
    # produces a new pair for the legitimate holder's next request, but a
    # thief who captured only the old token gets nothing further from it
    # (there's no server-side revocation list here, so this is best-effort,
    # not a substitute for one).
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> MeResponse:
    user = await _user_by_id(session, principal.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        can_view_salary=principal.is_admin,
        can_edit=principal.is_admin,
    )
