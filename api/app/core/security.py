from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> AppUser:
    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc

    user = await session.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


async def get_current_principal(user: AppUser = Depends(get_current_user)) -> Principal:
    return Principal(id=user.id, role=user.role)


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, Principal]]:

    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=403, detail=f"requires one of roles: {', '.join(roles)}"
            )
        return principal

    return _dependency
