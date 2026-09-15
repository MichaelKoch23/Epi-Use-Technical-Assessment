from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    email: str
    birth_date: date
    position: str
    salary: Decimal = Field(ge=0)
    currency: str = "ZAR"
    manager_id: uuid.UUID | None = None
    avatar_override_url: str | None = None


class EmployeeUpdate(BaseModel):
    """Partial update — every field optional. `manager_id` deliberately
    absent: reassignment is `PUT /employees/{id}/manager` (§6.1), not a
    general PATCH field, because it carries its own invariant."""

    employee_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    birth_date: date | None = None
    position: str | None = None
    salary: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    avatar_override_url: str | None = None


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


class EmployeeRead(_EmployeeReadBase):
    """Full representation — `hr_admin` only (§9.3)."""

    salary: Decimal


class EmployeeReadRestricted(_EmployeeReadBase):
    """`viewer` representation. `salary` is not a field here at all, so
    it is absent from the serialised payload — never null, never masked."""


EmployeeReadAny = EmployeeRead | EmployeeReadRestricted


class EmployeePage(BaseModel):
    items: list[EmployeeReadAny]
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
    action: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    occurred_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
