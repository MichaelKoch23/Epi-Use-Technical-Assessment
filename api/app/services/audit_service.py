from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.employee import Employee


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def snapshot_employee(employee: Employee) -> dict[str, Any]:
    """A JSONB-safe before/after snapshot of the fields an audit entry
    cares about. Not the ORM instance itself, so it stays valid after the
    instance's own fields change further in the same unit of work."""
    return {
        "employee_number": employee.employee_number,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "birth_date": _jsonable(employee.birth_date),
        "position": employee.position,
        "salary": _jsonable(employee.salary),
        "currency": employee.currency,
        "manager_id": _jsonable(employee.manager_id),
        "avatar_override_url": employee.avatar_override_url,
        "version": employee.version,
        "deleted_at": _jsonable(employee.deleted_at),
    }


class AuditService:
    """Writes `audit_log` rows. Every method here only adds to the
    session it was given and flushes — it never opens or commits a
    transaction of its own, so the audit row lives or dies with whatever
    change the caller is making in the same unit of work (§9.6)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        employee_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> AuditLog:
        entry = AuditLog(
            employee_id=employee_id,
            actor_id=actor_id,
            action=action,
            before=before,
            after=after,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_for_employee(
        self, employee_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[Sequence[AuditLog], int]:
        """Change history for one employee, newest first (§6.2)."""
        base = select(AuditLog).where(AuditLog.employee_id == employee_id)
        list_stmt = (
            base.order_by(AuditLog.occurred_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        count_stmt = select(func.count()).select_from(
            select(AuditLog.id).where(AuditLog.employee_id == employee_id).subquery()
        )

        items = (await self._session.execute(list_stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return items, total
