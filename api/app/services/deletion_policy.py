from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmployeeNotFound
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService, snapshot_employee
from app.services.employee_service import EmployeeService


@dataclass(frozen=True, slots=True)
class DeletionResult:
    deleted: list[Employee]
    reassigned: list[Employee]


@runtime_checkable
class DeletionPolicy(Protocol):
    """Strategy for what happens to an employee's direct reports when the
    employee is removed (§5.3). Selected per request; never applied
    silently by the UI without the caller having seen `affected` first."""

    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        """Employees this policy would touch, without writing anything —
        the preview a destructive delete requires before confirmation."""
        ...

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        """Perform the deletion (and any reparenting), auditing every
        change in the caller's transaction."""
        ...


class _BaseDeletionPolicy:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)
        self._employees = EmployeeService(session)

    async def _get_or_raise(self, employee_id: uuid.UUID) -> Employee:
        employee = await self._repo.get(employee_id)
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
        for report in reports:
            before = snapshot_employee(report)
            report.manager_id = new_manager_id
            report.version += 1
            after = snapshot_employee(report)
            await audit.record(
                employee_id=report.id,
                actor_id=actor_id,
                action="employee.reassigned",
                before=before,
                after=after,
            )
        await self._session.flush()


class Reparent(_BaseDeletionPolicy):
    """Direct reports move up to the deleted employee's own manager,
    preserving the chain. Deleting a root has no grandparent to move
    reports to, so `target.manager_id` is `None` and this degrades to
    `PromoteToRoot`'s behaviour without any special-casing."""

    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        target = await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)
        return [target, *reports]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        target = await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)

        await self._reassign_reports(reports, target.manager_id, actor_id=actor_id)
        deleted = await self._employees.soft_delete(employee_id, actor_id=actor_id)
        return DeletionResult(deleted=[deleted], reassigned=list(reports))


class PromoteToRoot(_BaseDeletionPolicy):
    """Direct reports become managerless and appear as new roots."""

    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        target = await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)
        return [target, *reports]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        await self._get_or_raise(employee_id)
        reports = await self._repo.get_direct_reports(employee_id)

        await self._reassign_reports(reports, None, actor_id=actor_id)
        deleted = await self._employees.soft_delete(employee_id, actor_id=actor_id)
        return DeletionResult(deleted=[deleted], reassigned=list(reports))


class Cascade(_BaseDeletionPolicy):
    """The entire subtree — the employee and every descendant — is
    soft-deleted. The UI must show `affected` and get explicit
    confirmation before calling `apply` with this policy (§5.3)."""

    async def affected(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        await self._get_or_raise(employee_id)
        subtree = await self._repo.get_subtree(employee_id)
        return [row.employee for row in subtree]

    async def apply(
        self, employee_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> DeletionResult:
        subtree = await self.affected(employee_id)
        deleted = [
            await self._employees.soft_delete(employee.id, actor_id=actor_id)
            for employee in subtree
        ]
        return DeletionResult(deleted=deleted, reassigned=[])


async def preview(employee_id: uuid.UUID, policy: DeletionPolicy) -> Sequence[Employee]:
    """The affected employees for `policy` applied to `employee_id`,
    without writing anything — the confirmation step the UI shows before
    a destructive delete (§5.3)."""
    return await policy.affected(employee_id)
