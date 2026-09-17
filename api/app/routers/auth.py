from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.avatars import resolve_avatar_url
from app.core.passwords import hash_password, verify_password
from app.core.rate_limit import login_rate_limiter
from app.core.security import Principal, get_current_principal, get_current_user
from app.core.tokens import decode_token
from app.db.session import get_db
from app.models.app_user import AppUser
from app.schemas.auth import LoginRequest, MeResponse, RefreshRequest, TokenPair
from app.services.session_service import (
    InvalidRefreshToken,
    IssuedTokens,
    SessionService,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_DUMMY_HASH = hash_password("not-a-real-password")

_INVALID_CREDENTIALS = "Incorrect email or password"


async def _user_by_id(session: AsyncSession, user_id: uuid.UUID) -> AppUser | None:
    return await session.get(AppUser, user_id)


def _token_pair(tokens: IssuedTokens) -> TokenPair:
    return TokenPair(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


def _subject(payload: dict[str, object]) -> uuid.UUID:
    try:
        return uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc


def _jti(payload: dict[str, object]) -> uuid.UUID:
    try:
        return uuid.UUID(str(payload["jti"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


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
        raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)

    tokens = await SessionService(session).issue(user)
    await session.commit()
    return _token_pair(tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest, session: AsyncSession = Depends(get_db)
) -> TokenPair:
    payload = decode_token(body.refresh_token, expected_type="refresh")
    user_id = _subject(payload)
    jti = _jti(payload)

    user = await _user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")

    try:
        tokens = await SessionService(session).rotate(user, jti)
    except InvalidRefreshToken as exc:
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    await session.commit()
    return _token_pair(tokens)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Response:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
        await SessionService(session).revoke(_jti(payload), principal.id)
        await session.commit()
    except HTTPException:
        pass
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
async def me(user: AppUser = Depends(get_current_user)) -> MeResponse:
    is_admin = user.role == "hr_admin"
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        avatar_url=resolve_avatar_url(
            avatar_override_url=user.avatar_override_url, email=user.email
        ),
        can_view_salary=is_admin,
        can_edit=is_admin,
    )
