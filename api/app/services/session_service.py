from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import (
    create_access_token,
    create_refresh_token,
    refresh_token_expiry,
)
from app.models.app_user import AppUser
from app.models.refresh_token import RefreshToken


class InvalidRefreshToken(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, user: AppUser) -> IssuedTokens:
        record = RefreshToken(user_id=user.id, expires_at=refresh_token_expiry())
        self._session.add(record)
        await self._session.flush()
        return IssuedTokens(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, record.id),
        )

    async def rotate(self, user: AppUser, jti: uuid.UUID) -> IssuedTokens:
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.id == jti).with_for_update()
            )
        ).scalar_one_or_none()

        if record is None or record.user_id != user.id:
            raise InvalidRefreshToken

        now = datetime.now(UTC)

        if record.revoked_at is not None:
            await self.revoke_all_for_user(user.id)
            raise InvalidRefreshToken

        if record.expires_at <= now:
            raise InvalidRefreshToken

        successor = RefreshToken(user_id=user.id, expires_at=refresh_token_expiry())
        self._session.add(successor)
        await self._session.flush()

        record.revoked_at = now
        record.replaced_by = successor.id
        await self._session.flush()

        return IssuedTokens(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, successor.id),
        )

    async def revoke(self, jti: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.id == jti,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
