"""`/api/v1/employees/*` — §6.2 of the technical design, the employee-scoped
rows of the endpoint table (hierarchy/analytics/import-export/auth/search
are separate routers, not built yet)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmployeeNotFound
from app.core.pagination import (
    EmployeeSortParams,
    PageParams,
    employee_filter_params,
    employee_sort_params,
    page_params,
)
from app.core.security import Principal, get_current_principal, require_admin
from app.db.session import get_db
from app.models.employee import Employee
from app.repositories.employee_repository import (
    EmployeeListFilters,
    EmployeeListRow,
    EmployeeRepository,
)
from app.schemas.employee import (
    AuditLogPage,
    AuditLogRead,
    EmployeeCreate,
    EmployeeHierarchyNode,
    EmployeeListItemRead,
    EmployeeListItemReadAny,
    EmployeeListItemReadRestricted,
    EmployeePage,
    EmployeeRead,
    EmployeeReadAny,
    EmployeeReadRestricted,
    EmployeeUpdate,
    ManagerReassignRequest,
)
from app.services.audit_service import AuditService
from app.services.deletion_policy import (
    Cascade,
    DeletionPolicy,
    PromoteToRoot,
    Reparent,
    preview,
)
from app.services.employee_service import EmployeeService
from app.services.reassignment_service import ReassignmentService

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])

DeletionPolicyName = Literal["reparent", "promote_to_root", "cascade"]

_POLICY_CLASSES: dict[str, Callable[[AsyncSession], DeletionPolicy]] = {
    "reparent": Reparent,
    "promote_to_root": PromoteToRoot,
    "cascade": Cascade,
}


def _policy_for(name: DeletionPolicyName, session: AsyncSession) -> DeletionPolicy:
    return _POLICY_CLASSES[name](session)


def _parse_if_match(value: str) -> int:
    """`If-Match: "<version>"` (§3.5) — a quoted integer version."""
    try:
        return int(value.strip('"'))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="If-Match header must be a quoted integer version"
        ) from exc


def to_employee_read(employee: Employee, principal: Principal) -> EmployeeReadAny:
    """Response schema selection by role (§9.3): a `viewer` gets a payload
    where `salary` is not a key at all, not a null value."""
    if principal.is_admin:
        return EmployeeRead.model_validate(employee)
    return EmployeeReadRestricted.model_validate(employee)


def to_employee_list_item(
    row: EmployeeListRow, principal: Principal
) -> EmployeeListItemReadAny:
    base = to_employee_read(row.employee, principal)
    merged = {
        **base.model_dump(),
        "manager_name": row.manager_name,
        "direct_report_count": row.direct_report_count,
    }
    if principal.is_admin:
        return EmployeeListItemRead.model_validate(merged)
    return EmployeeListItemReadRestricted.model_validate(merged)


def _require_salary_access(
    principal: Principal, filters: EmployeeListFilters, sort: str
) -> None:
    """§9.3: salary-based filtering or sorting would let a viewer infer
    the value by binary search, so both are rejected outright for them."""
    if principal.is_admin:
        return
    if (
        filters.min_salary is not None
        or filters.max_salary is not None
        or sort == "salary"
    ):
        raise HTTPException(
            status_code=403,
            detail="salary-based filtering or sorting requires hr_admin",
        )


@router.get("", response_model=EmployeePage)
async def list_employees(
    filters: EmployeeListFilters = Depends(employee_filter_params),
    sort_params: EmployeeSortParams = Depends(employee_sort_params),
    pagination: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> EmployeePage:
    _require_salary_access(principal, filters, sort_params.sort)

    repo = EmployeeRepository(session)
    items, total = await repo.list(
        filters,
        sort=sort_params.sort,
        order=sort_params.order,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return EmployeePage(
        items=[to_employee_list_item(row, principal) for row in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=EmployeeRead, status_code=201)
async def create_employee(
    body: EmployeeCreate,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> EmployeeRead:
    service = EmployeeService(session)
    employee = await service.create(**body.model_dump(), actor_id=principal.id)
    await session.commit()
    return EmployeeRead.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeReadAny)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> EmployeeReadAny:
    repo = EmployeeRepository(session)
    employee = await repo.get(employee_id)
    if employee is None:
        raise EmployeeNotFound(employee_id)
    return to_employee_read(employee, principal)


@router.patch("/{employee_id}", response_model=EmployeeReadAny)
async def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeUpdate,
    if_match: str = Header(..., alias="If-Match"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> EmployeeReadAny:
    service = EmployeeService(session)
    employee = await service.update(
        employee_id,
        expected_version=_parse_if_match(if_match),
        actor_id=principal.id,
        **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return to_employee_read(employee, principal)


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: uuid.UUID,
    policy: DeletionPolicyName = Query("reparent"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> None:
    await _policy_for(policy, session).apply(employee_id, actor_id=principal.id)
    await session.commit()


@router.post("/{employee_id}/restore", response_model=EmployeeReadAny)
async def restore_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> EmployeeReadAny:
    service = EmployeeService(session)
    employee = await service.restore(employee_id, actor_id=principal.id)
    await session.commit()
    return to_employee_read(employee, principal)


@router.get("/{employee_id}/deletion-preview", response_model=list[EmployeeReadAny])
async def deletion_preview(
    employee_id: uuid.UUID,
    policy: DeletionPolicyName = Query("reparent"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> list[EmployeeReadAny]:
    affected = await preview(employee_id, _policy_for(policy, session))
    return [to_employee_read(e, principal) for e in affected]


@router.put("/{employee_id}/manager", response_model=EmployeeReadAny)
async def reassign_manager(
    employee_id: uuid.UUID,
    body: ManagerReassignRequest,
    if_match: str = Header(..., alias="If-Match"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> EmployeeReadAny:
    service = ReassignmentService(session)
    employee = await service.reassign_manager(
        employee_id,
        body.manager_id,
        expected_version=_parse_if_match(if_match),
        actor_id=principal.id,
    )
    await session.commit()
    return to_employee_read(employee, principal)


@router.get("/{employee_id}/subtree", response_model=list[EmployeeHierarchyNode])
async def get_subtree(
    employee_id: uuid.UUID,
    depth: int | None = Query(None, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[EmployeeHierarchyNode]:
    repo = EmployeeRepository(session)
    if await repo.get(employee_id) is None:
        raise EmployeeNotFound(employee_id)

    rows = await repo.get_subtree(employee_id, max_depth=depth)
    return [
        EmployeeHierarchyNode(
            employee=to_employee_read(row.employee, principal), depth=row.depth
        )
        for row in rows
    ]


@router.get("/{employee_id}/reporting-line", response_model=list[EmployeeHierarchyNode])
async def get_reporting_line(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[EmployeeHierarchyNode]:
    repo = EmployeeRepository(session)
    if await repo.get(employee_id) is None:
        raise EmployeeNotFound(employee_id)

    rows = await repo.get_ancestors(employee_id)
    return [
        EmployeeHierarchyNode(
            employee=to_employee_read(row.employee, principal), depth=row.depth
        )
        for row in rows
    ]


@router.get("/{employee_id}/audit", response_model=AuditLogPage)
async def get_employee_audit(
    employee_id: uuid.UUID,
    pagination: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> AuditLogPage:
    repo = EmployeeRepository(session)
    if await repo.get_any(employee_id) is None:
        raise EmployeeNotFound(employee_id)

    audit = AuditService(session)
    entries, total = await audit.list_for_employee(
        employee_id, page=pagination.page, page_size=pagination.page_size
    )
    return AuditLogPage(
        items=[AuditLogRead.model_validate(e) for e in entries],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
