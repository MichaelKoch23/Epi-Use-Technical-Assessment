"""Principal resolution for the API layer.

There is no JWT issuance/verification yet (§9.1 — access/refresh tokens,
Argon2id password hashing, `/auth/login`) — that is a separate, not-yet-built
piece of work. Until it exists, the principal is resolved from an
`X-Actor-Id` header naming an existing `app_user` row, so that role-based
response shaping and audit attribution (both required now) have something
real to work against rather than being faked out in every router.

`get_current_principal` / `require_admin` are the seam: swapping this
module's internals for real JWT verification later changes nothing about
how routers consume it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.app_user import AppUser


@dataclass(frozen=True, slots=True)
class Principal:
    id: uuid.UUID
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "hr_admin"


async def get_current_principal(
    x_actor_id: uuid.UUID = Header(
        ...,
        alias="X-Actor-Id",
        description="Temporary stand-in for a JWT subject (§9.1 not yet built): "
        "the id of an existing app_user row to act as.",
    ),
    session: AsyncSession = Depends(get_db),
) -> Principal:
    user = (
        await session.execute(select(AppUser).where(AppUser.id == x_actor_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown actor")
    return Principal(id=user.id, role=user.role)


async def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="hr_admin role required")
    return principal
