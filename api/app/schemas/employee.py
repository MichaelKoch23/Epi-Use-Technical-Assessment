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
    Salary,
)


class EmployeeCreate(BaseModel):
    # `extra="forbid"` so a typo'd or renamed field is a 422 naming the
    # unknown key, rather than a silently ignored write the caller
    # believes succeeded.
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
    """Partial update - every field optional. `manager_id` deliberately
    absent: reassignment is `PUT /employees/{id}/manager` (§6.1), not a
    general PATCH field, because it carries its own invariant.

    Every field that *is* here is `Optional` only in the "may be omitted"
    sense - `exclude_unset=True` in the router means an omitted field is
    never passed on. None of them accept an explicit `null` except
    `avatar_override_url`, which is the one column that is genuinely
    nullable."""

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
    manager_id: uuid.UUID | None


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
    """Full representation - `hr_admin` only (§9.3)."""

    salary: Decimal


class EmployeeReadRestricted(_EmployeeReadBase):
    """`viewer` representation. `salary` is not a field here at all, so
    it is absent from the serialised payload - never null, never masked."""


EmployeeReadAny = EmployeeRead | EmployeeReadRestricted


class EmployeeListItemRead(EmployeeRead):
    """`EmployeeRead` plus fields only the list endpoint bothers to compute
    (§list query in the repository) - a manager's display name in place of
    a bare id, and the row's own direct-report count."""

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
    # True/False whenever `before`/`after` are both present and their raw
    # `salary` values differ - computed before any role-based redaction, so
    # a viewer who never sees the values themselves can still see *that* a
    # change happened (§9.3 extended to the audit trail).
    salary_changed: bool
    # Only populated for `employee.reassigned` entries - `before`/`after`
    # only carry a bare `manager_id` UUID, which isn't renderable as a
    # human diff on its own (§ audit timeline UI).
    manager_before_name: str | None = None
    manager_after_name: str | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int


class GlobalAuditLogRead(AuditLogRead):
    """`AuditLogRead` plus which employee the entry is about - the
    per-employee page already has that from context, but the global feed
    behind the topbar's "Change history" button spans every employee at
    once (§ global audit feed)."""

    employee_name: str


class GlobalAuditLogPage(BaseModel):
    items: list[GlobalAuditLogRead]
    total: int
    page: int
    page_size: int
