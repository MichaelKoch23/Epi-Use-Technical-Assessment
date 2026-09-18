from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.avatars import resolve_avatar_url
from app.schemas.fields import (
    AvatarOverrideUrl,
    BirthDate,
    Currency,
    Email,
    EmployeeNumber,
    PersonName,
    Position,
    ReassignReason,
    Salary,
)


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_number: EmployeeNumber
    first_name: PersonName
    last_name: PersonName
    email: Email
    birth_date: BirthDate
    position: Position
    salary: Salary
    currency: Currency = "ZAR"
    manager_id: uuid.UUID | None = None
    avatar_override_url: AvatarOverrideUrl = None


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_number: EmployeeNumber | None = None
    first_name: PersonName | None = None
    last_name: PersonName | None = None
    email: Email | None = None
    birth_date: BirthDate | None = None
    position: Position | None = None
    salary: Salary | None = None
    currency: Currency | None = None
    avatar_override_url: AvatarOverrideUrl = None


class ManagerReassignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manager_id: uuid.UUID | None
    # A past date is permitted - corrections are legitimate - but the service
    # refuses one that precedes the employee's first recorded assignment.
    effective_from: date | None = None
    reason: ReassignReason = None


class GravatarPrefillRead(BaseModel):
    """A suggestion drawn from a public Gravatar profile, never applied on its own."""

    found: bool
    hash: str
    avatar_url: str | None = None
    profile_url: str | None = None
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None


class ManagerOptionRead(BaseModel):
    """A manager offered as a choice, with just enough to tell two apart."""

    id: uuid.UUID
    first_name: str
    last_name: str
    employee_number: str


class _EmployeeReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_number: str
    first_name: str
    last_name: str
    email: str
    birth_date: date
    position: str
    currency: str
    manager_id: uuid.UUID | None
    avatar_override_url: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avatar_url(self) -> str:
        return resolve_avatar_url(
            avatar_override_url=self.avatar_override_url, email=self.email
        )


class EmployeeRead(_EmployeeReadBase):
    salary: Decimal


class EmployeeReadRestricted(_EmployeeReadBase):
    pass


EmployeeReadAny = EmployeeRead | EmployeeReadRestricted


class EmployeeListItemRead(EmployeeRead):
    manager_name: str | None
    direct_report_count: int


class EmployeeListItemReadRestricted(EmployeeReadRestricted):
    manager_name: str | None
    direct_report_count: int


EmployeeListItemReadAny = EmployeeListItemRead | EmployeeListItemReadRestricted


class EmployeePage(BaseModel):
    items: list[EmployeeListItemReadAny]
    total: int
    page: int
    page_size: int


class EmployeeHierarchyNode(BaseModel):
    employee: EmployeeReadAny
    depth: int


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    actor_id: uuid.UUID
    actor_email: str
    action: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    occurred_at: datetime
    salary_changed: bool
    manager_before_name: str | None = None
    manager_after_name: str | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int


class GlobalAuditLogRead(AuditLogRead):
    employee_name: str


class GlobalAuditLogPage(BaseModel):
    items: list[GlobalAuditLogRead]
    total: int
    page: int
    page_size: int
