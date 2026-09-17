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
        chain = [new_manager_id]
        for ancestor in await self._repo.get_ancestors(new_manager_id):
            chain.append(ancestor.employee.id)
            if ancestor.employee.id == employee_id:
                break
        return chain
