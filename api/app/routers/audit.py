from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, page_params
from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.repositories.employee_repository import EmployeeRepository
from app.routers.employees import audit_log_fields
from app.schemas.employee import GlobalAuditLogPage, GlobalAuditLogRead
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=GlobalAuditLogPage)
async def list_audit_log(
    pagination: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> GlobalAuditLogPage:
    audit = AuditService(session)
    rows, total = await audit.list_all(
        page=pagination.page, page_size=pagination.page_size
    )

    repo = EmployeeRepository(session)
    employee_ids = {row.entry.employee_id for row in rows}
    employee_names = await repo.get_names_by_ids(list(employee_ids))

    manager_ids = {
        uuid.UUID(snapshot["manager_id"])
        for row in rows
        if row.entry.action == "employee.reassigned"
        for snapshot in (row.entry.before, row.entry.after)
        if snapshot is not None and snapshot.get("manager_id") is not None
    }
    manager_names = await repo.get_names_by_ids(list(manager_ids))

    items = [
        GlobalAuditLogRead(
            **audit_log_fields(row, principal, manager_names),
            employee_name=employee_names.get(row.entry.employee_id, "Unknown employee"),
        )
        for row in rows
    ]
    return GlobalAuditLogPage(
        items=items, total=total, page=pagination.page, page_size=pagination.page_size
    )
