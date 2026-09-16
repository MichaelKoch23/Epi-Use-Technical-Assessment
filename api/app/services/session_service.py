"""Refresh-token lifecycle (§9.1): issue, rotate, revoke.

A signature proves a token came from this server. It cannot prove the
token is still meant to work - that a user has not logged out since, and
that the token has not already been spent. That second question is what
the `refresh_token` table answers, and this service is the only thing
that reads or writes it.

The rotation scheme is the standard one for public clients that must hold
a long-lived credential in storage they do not fully control:

* Each refresh spends the presented token and issues a successor, chained
  through `replaced_by`.
* Presenting an *already spent* token is the signal that two parties hold
  the same credential - the legitimate client and a thief. There is no way
  to tell which one is calling, so the entire chain is revoked and both
  are forced back through the password. A stolen token therefore buys an
  attacker access only until the real user's next refresh, instead of the
  full seven days.
"""

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
    """The presented token is unknown, expired, or already spent."""


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, user: AppUser) -> IssuedTokens:
        """A fresh session - called on successful login."""
        record = RefreshToken(user_id=user.id, expires_at=refresh_token_expiry())
        self._session.add(record)
        await self._session.flush()  # assigns the jti
        return IssuedTokens(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, record.id),
        )

    async def rotate(self, user: AppUser, jti: uuid.UUID) -> IssuedTokens:
        """Spend `jti` and issue its successor.

        Raises `InvalidRefreshToken` if the token is unknown, expired,
        belongs to someone else, or has already been spent - the last of
        which also revokes every other live token for the user.
        """
        record = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.id == jti).with_for_update()
            )
        ).scalar_one_or_none()

        if record is None or record.user_id != user.id:
            raise InvalidRefreshToken

        now = datetime.now(UTC)

        if record.revoked_at is not None:
            # Replay. The token was spent once already, so whoever is
            # calling now is not the only holder. Burn the whole family:
            # it is better to make the real user log in again than to keep
            # serving both of them.
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
        """End one session - logout. Idempotent, and scoped to the caller's
        own user so one account cannot end another's session."""
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
        """End every live session for a user - sign-out-everywhere, and the
        response to detected replay."""
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
