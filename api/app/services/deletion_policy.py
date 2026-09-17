from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmployeeNotFound
from app.models.employee import Employee
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService, snapshot_employee
from app.services.employee_service import EmployeeService


@dataclass(frozen=True, slots=True)
class DeletionResult:
    deleted: list[Employee]
    reassigned: list[Employee]


@runtime_checkable
class DeletionPolicy(Protocol):
    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]: ...

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult: ...


class _BaseDeletionPolicy:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)
        self._assignments = AssignmentRepository(session)
        self._employees = EmployeeService(session)

    async def _get_or_raise(self, employee_id: uuid.UUID) -> Employee:
        employee = await self._repo.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        return employee

    async def _lock_or_raise(self, employee_id: uuid.UUID) -> Employee:
        employee = await self._repo.get_for_update(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        return employee

    async def _reassign_reports(
        self,
        reports: Sequence[Employee],
        new_manager_id: uuid.UUID | None,
        *,
        actor_id: uuid.UUID,
    ) -> None:
        audit = AuditService(self._session)
        today = datetime.now(UTC).date()
        for report in reports:
            before = snapshot_employee(report)
            report.manager_id = new_manager_id
            report.version += 1
            after = snapshot_employee(report)
            await self._session.flush()
            await self._assignments.set_edge(
                report.id,
                new_manager_id,
                effective_from=today,
                reason="Manager deleted",
                created_by=actor_id,
            )
            await audit.record(
                employee_id=report.id,
                actor_id=actor_id,
                action="employee.reassigned",
                before=before,
                after=after,
            )
        await self._session.flush()


class Reparent(_BaseDeletionPolicy):
    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        target = await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)
        return [target, *reports]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        target = await self._lock_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)

        await self._reassign_reports(reports, target.manager_id, actor_id=actor_id)
        deleted = await self._employees.soft_delete(employee_id, actor_id=actor_id)
        return DeletionResult(deleted=[deleted], reassigned=list(reports))


class PromoteToRoot(_BaseDeletionPolicy):
    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        target = await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)
        return [target, *reports]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        await self._lock_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)

        await self._reassign_reports(reports, None, actor_id=actor_id)
        deleted = await self._employees.soft_delete(employee_id, actor_id=actor_id)
        return DeletionResult(deleted=[deleted], reassigned=list(reports))


class Cascade(_BaseDeletionPolicy):
    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        await self._get_or_raise(employee_id)
        subtree = await self._repo.get_subtree(employee_id)
        return [row.employee for row in subtree]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        await self._lock_or_raise(employee_id)
        subtree = await self.affected(employee_id)
        deleted = [
            await self._employees.soft_delete(employee.id, actor_id=actor_id)
            for employee in subtree
        ]
        return DeletionResult(deleted=deleted, reassigned=[])


async def preview(employee_id: uuid.UUID, policy: DeletionPolicy) -> Sequence[Employee]:
    return await policy.affected(employee_id)
