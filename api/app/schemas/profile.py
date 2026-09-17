from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProfilePerson(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    position: str
    avatar_url: str


class ProfileEmployee(ProfilePerson):
    employee_number: str
    email: str
    joined_at: datetime
    manager: ProfilePerson | None
    direct_reports: list[ProfilePerson]


class ProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    can_view_salary: bool
    can_edit: bool
    avatar_url: str
    gravatar_url: str
    has_uploaded_avatar: bool
    employee: ProfileEmployee | None
