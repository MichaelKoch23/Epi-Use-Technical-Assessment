from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_user import AppUser
from app.models.audit_log import AuditLog
from app.models.employee import Employee


@dataclass(frozen=True, slots=True)
class AuditLogRow:
    entry: AuditLog
    actor_email: str


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def snapshot_employee(employee: Employee) -> dict[str, Any]:
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


def _newest_first() -> tuple[Any, Any]:
    return AuditLog.occurred_at.desc(), AuditLog.id.desc()


class AuditService:
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
    ) -> tuple[Sequence[AuditLogRow], int]:
        base = (
            select(AuditLog, AppUser.email)
            .join(AppUser, AppUser.id == AuditLog.actor_id)
            .where(AuditLog.employee_id == employee_id)
        )
        list_stmt = (
            base.order_by(*_newest_first())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        count_stmt = select(func.count()).select_from(
            select(AuditLog.id).where(AuditLog.employee_id == employee_id).subquery()
        )

        rows = (await self._session.execute(list_stmt)).all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        items = [AuditLogRow(entry=entry, actor_email=email) for entry, email in rows]
        return items, total

    async def list_all(
        self, *, page: int = 1, page_size: int = 50
    ) -> tuple[Sequence[AuditLogRow], int]:
        base = select(AuditLog, AppUser.email).join(
            AppUser, AppUser.id == AuditLog.actor_id
        )
        list_stmt = (
            base.order_by(*_newest_first())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        count_stmt = select(func.count()).select_from(AuditLog)

        rows = (await self._session.execute(list_stmt)).all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        items = [AuditLogRow(entry=entry, actor_email=email) for entry, email in rows]
        return items, total
