from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateEmployeeNumberError,
    EmployeeNotFound,
    VersionConflictError,
)
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService, snapshot_employee


@dataclass(frozen=True, slots=True)
class _UnsetType:
    """Sentinel distinguishing "field not supplied" from "field explicitly
    set to None" in a partial update, without collapsing the two."""

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _UnsetType()


class EmployeeService:
    """Create, update, soft-delete and restore individual employee
    records. Manager reassignment is deliberately not here — it carries
    its own invariant (acyclicity) and its own dedicated sub-resource
    (§6.1), so it lives in `ReassignmentService`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)
        self._audit = AuditService(session)

    async def create(
        self,
        *,
        employee_number: str,
        first_name: str,
        last_name: str,
        email: str,
        birth_date: date,
        position: str,
        salary: Decimal,
        currency: str = "ZAR",
        manager_id: uuid.UUID | None = None,
        avatar_override_url: str | None = None,
        actor_id: uuid.UUID,
    ) -> Employee:
        if await self._repo.get_by_employee_number(employee_number) is not None:
            raise DuplicateEmployeeNumberError(employee_number)

        employee = Employee(
            employee_number=employee_number,
            first_name=first_name,
            last_name=last_name,
            email=email,
            birth_date=birth_date,
            position=position,
            salary=salary,
            currency=currency,
            manager_id=manager_id,
            avatar_override_url=avatar_override_url,
        )
        self._session.add(employee)
        # Flush now (not just add) so id/defaults are assigned and any
        # constraint violation surfaces here rather than at the audit write.
        await self._session.flush()

        await self._audit.record(
            employee_id=employee.id,
            actor_id=actor_id,
            action="employee.created",
            before=None,
            after=snapshot_employee(employee),
        )
        return employee

    async def update(
        self,
        employee_id: uuid.UUID,
        *,
        expected_version: int,
        actor_id: uuid.UUID,
        employee_number: str | _UnsetType = UNSET,
        first_name: str | _UnsetType = UNSET,
        last_name: str | _UnsetType = UNSET,
        email: str | _UnsetType = UNSET,
        birth_date: date | _UnsetType = UNSET,
        position: str | _UnsetType = UNSET,
        salary: Decimal | _UnsetType = UNSET,
        currency: str | _UnsetType = UNSET,
        avatar_override_url: str | None | _UnsetType = UNSET,
    ) -> Employee:
        employee = await self._repo.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        if employee.version != expected_version:
            raise VersionConflictError(employee_id, expected_version, employee.version)

        if (
            not isinstance(employee_number, _UnsetType)
            and employee_number != employee.employee_number
        ):
            clash = await self._repo.get_by_employee_number(employee_number)
            if clash is not None and clash.id != employee.id:
                raise DuplicateEmployeeNumberError(employee_number)

        before = snapshot_employee(employee)

        for field, value in (
            ("employee_number", employee_number),
            ("first_name", first_name),
            ("last_name", last_name),
            ("email", email),
            ("birth_date", birth_date),
            ("position", position),
            ("salary", salary),
            ("currency", currency),
            ("avatar_override_url", avatar_override_url),
        ):
            if value is not UNSET:
                setattr(employee, field, value)

        employee.version += 1
        after = snapshot_employee(employee)

        await self._session.flush()
        await self._audit.record(
            employee_id=employee.id,
            actor_id=actor_id,
            action="employee.updated",
            before=before,
            after=after,
        )
        return employee

    async def soft_delete(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> Employee:
        employee = await self._repo.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)

        before = snapshot_employee(employee)
        employee.deleted_at = datetime.now(UTC)
        employee.version += 1
        after = snapshot_employee(employee)

        await self._session.flush()
        await self._audit.record(
            employee_id=employee.id,
            actor_id=actor_id,
            action="employee.deleted",
            before=before,
            after=after,
        )
        return employee

    async def restore(self, employee_id: uuid.UUID, *, actor_id: uuid.UUID) -> Employee:
        employee = await self._repo.get_any(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        if employee.deleted_at is None:
            return employee  # already active: idempotent no-op, nothing to audit

        before = snapshot_employee(employee)
        employee.deleted_at = None
        employee.version += 1
        after = snapshot_employee(employee)

        await self._session.flush()
        await self._audit.record(
            employee_id=employee.id,
            actor_id=actor_id,
            action="employee.restored",
            before=before,
            after=after,
        )
        return employee
