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
    """The employee record whose email matches the signed-in account."""

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
    # What the app shows: the uploaded photo if there is one, else Gravatar.
    avatar_url: str
    # Always the Gravatar image, so the page can say whether one exists
    # independently of any upload that is currently hiding it.
    gravatar_url: str
    has_uploaded_avatar: bool
    employee: ProfileEmployee | None
