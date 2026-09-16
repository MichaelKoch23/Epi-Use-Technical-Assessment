from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmployeeNotFound,
    ReportingCycleError,
    VersionConflictError,
)
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService, snapshot_employee


class ReassignmentService:
    """Changes an employee's manager. This is the one write path with a
    real concurrency hazard (§5.2): two instances of this service, in two
    separate processes, can each validate a reassignment against a
    snapshot that predates the other and jointly commit a cycle that
    neither could have created alone. Three layers close that off, only
    the first two of which live here:

    1. Row-level locking, in a deterministic order, so two conflicting
       moves on the same rows serialise instead of deadlocking.
    2. A pre-write subtree check giving a clear, actionable error.
    3. A deferred constraint trigger at COMMIT (`employee_no_cycle`),
       which is the actual authority - it closes the race this service
       cannot see across processes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)
        self._audit = AuditService(session)

    async def reassign_manager(
        self,
        employee_id: uuid.UUID,
        new_manager_id: uuid.UUID | None,
        *,
        expected_version: int,
        actor_id: uuid.UUID,
    ) -> Employee:
        # Lock every row this write touches in a fixed (id-sorted) order,
        # regardless of which argument each id came in as. Two concurrent,
        # opposite reassignments (A under B, B under A) then contend for
        # the same first lock instead of each holding one lock the other
        # needs - a deadlock rather than a race.
        ids_to_lock = sorted(
            {employee_id} | ({new_manager_id} if new_manager_id else set())
        )
        locked: dict[uuid.UUID, Employee] = {}
        for row_id in ids_to_lock:
            row = await self._repo.get_for_update(row_id)
            if row is None:
                raise EmployeeNotFound(row_id)
            locked[row_id] = row

        employee = locked[employee_id]
        if employee.version != expected_version:
            raise VersionConflictError(employee_id, expected_version, employee.version)

        if new_manager_id is not None:
            if new_manager_id == employee_id:
                raise ReportingCycleError(employee_id, new_manager_id, [employee_id])

            if await self._repo.is_descendant(new_manager_id, employee_id):
                chain = await self._cycle_chain(employee_id, new_manager_id)
                raise ReportingCycleError(employee_id, new_manager_id, chain)

        before = snapshot_employee(employee)
        employee.manager_id = new_manager_id
        employee.version += 1
        after = snapshot_employee(employee)

        await self._session.flush()
        await self._audit.record(
            employee_id=employee.id,
            actor_id=actor_id,
            action="employee.reassigned",
            before=before,
            after=after,
        )
        return employee

    async def _cycle_chain(
        self, employee_id: uuid.UUID, new_manager_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """The existing reporting path from `new_manager_id` up to
        `employee_id` - the path the proposed assignment would close into
        a loop, for a message like the one in §6.4."""
        chain = [new_manager_id]
        for ancestor in await self._repo.get_ancestors(new_manager_id):
            chain.append(ancestor.employee.id)
            if ancestor.employee.id == employee_id:
                break
        return chain
