from __future__ import annotations

import uuid

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    # Uploaded account photo if set, else the account email's Gravatar.
    avatar_url: str
    can_view_salary: bool
    can_edit: bool
