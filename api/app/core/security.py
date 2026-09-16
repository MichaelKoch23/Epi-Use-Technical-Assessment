"""Principal resolution for the API layer (§9.1/§9.2).

`get_current_principal` verifies a JWT access token (`POST /auth/login`
issues it) and loads the `app_user` row it names - a role change takes
effect the moment that token expires, rather than being cached for its
lifetime. `require_role` is the route-level authorisation dependency
(§9.2): "an endpoint cannot be added without a policy decision being
made explicitly" means every write endpoint names its own
`Depends(require_role("hr_admin"))` rather than a single blanket check.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import decode_token
from app.db.session import get_db
from app.models.app_user import AppUser

_bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True, slots=True)
class Principal:
    id: uuid.UUID
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "hr_admin"


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> Principal:
    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc

    user = (
        await session.execute(select(AppUser).where(AppUser.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return Principal(id=user.id, role=user.role)


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """A route-level dependency factory: `Depends(require_role("hr_admin"))`
    on a route reads, at the route, exactly who may call it."""

    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=403, detail=f"requires one of roles: {', '.join(roles)}"
            )
        return principal

    return _dependency
