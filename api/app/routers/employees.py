from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmployeeNotFound
from app.core.pagination import (
    EmployeeSortParams,
    PageParams,
    employee_filter_params,
    employee_sort_params,
    page_params,
)
from app.core.security import Principal, get_current_principal, require_role
from app.core.uploads import read_capped
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
from app.services.audit_service import AuditLogRow, AuditService
from app.services.avatar_service import MAX_AVATAR_BYTES, AvatarService
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
    try:
        return int(value.strip('"'))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="If-Match header must be a quoted integer version"
        ) from exc


def to_employee_read(employee: Employee, principal: Principal) -> EmployeeReadAny:
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


def _strip_salary(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {key: value for key, value in snapshot.items() if key != "salary"}


def audit_log_fields(
    row: AuditLogRow,
    principal: Principal,
    manager_names: dict[uuid.UUID, str],
) -> dict[str, Any]:
    entry = row.entry
    before, after = entry.before, entry.after
    salary_changed = (
        before is not None
        and after is not None
        and before.get("salary") != after.get("salary")
    )

    manager_before_name = manager_after_name = None
    if entry.action == "employee.reassigned":
        if before is not None and before.get("manager_id") is not None:
            manager_before_name = manager_names.get(uuid.UUID(before["manager_id"]))
        if after is not None and after.get("manager_id") is not None:
            manager_after_name = manager_names.get(uuid.UUID(after["manager_id"]))

    if not principal.is_admin:
        before = _strip_salary(before)
        after = _strip_salary(after)

    return {
        "id": entry.id,
        "employee_id": entry.employee_id,
        "actor_id": entry.actor_id,
        "actor_email": row.actor_email,
        "action": entry.action,
        "before": before,
        "after": after,
        "occurred_at": entry.occurred_at,
        "salary_changed": salary_changed,
        "manager_before_name": manager_before_name,
        "manager_after_name": manager_after_name,
    }


def to_audit_log_read(
    row: AuditLogRow,
    principal: Principal,
    manager_names: dict[uuid.UUID, str],
) -> AuditLogRead:
    return AuditLogRead(**audit_log_fields(row, principal, manager_names))


def require_salary_access(
    principal: Principal, filters: EmployeeListFilters, sort: str
) -> None:
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
    require_salary_access(principal, filters, sort_params.sort)

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
    principal: Principal = Depends(require_role("hr_admin")),
) -> EmployeeRead:
    service = EmployeeService(session)
    employee = await service.create(**body.model_dump(), actor_id=principal.id)
    await session.commit()
    return EmployeeRead.model_validate(employee)


@router.get("/positions", response_model=list[str])
async def list_positions(
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(get_current_principal),
) -> list[str]:
    return list(await EmployeeRepository(session).list_positions())


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
    principal: Principal = Depends(require_role("hr_admin")),
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


async def _set_avatar(
    session: AsyncSession,
    employee_id: uuid.UUID,
    new_url: str | None,
    *,
    if_match: str,
    principal: Principal,
) -> EmployeeReadAny:
    repo = EmployeeRepository(session)
    current = await repo.get(employee_id)
    if current is None:
        raise EmployeeNotFound(employee_id)
    previous_url = current.avatar_override_url

    employee = await EmployeeService(session).update(
        employee_id,
        expected_version=_parse_if_match(if_match),
        actor_id=principal.id,
        avatar_override_url=new_url,
    )
    if previous_url != new_url:
        await AvatarService(session).discard_if_unused(previous_url)
    await session.commit()
    return to_employee_read(employee, principal)


@router.put("/{employee_id}/avatar", response_model=EmployeeReadAny)
async def upload_employee_avatar(
    employee_id: uuid.UUID,
    file: UploadFile = File(...),
    if_match: str = Header(..., alias="If-Match"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> EmployeeReadAny:
    raw = await read_capped(file, MAX_AVATAR_BYTES, what="Image")
    url = await AvatarService(session).store(raw)
    return await _set_avatar(
        session, employee_id, url, if_match=if_match, principal=principal
    )


@router.delete("/{employee_id}/avatar", response_model=EmployeeReadAny)
async def remove_employee_avatar(
    employee_id: uuid.UUID,
    if_match: str = Header(..., alias="If-Match"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> EmployeeReadAny:
    return await _set_avatar(
        session, employee_id, None, if_match=if_match, principal=principal
    )


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: uuid.UUID,
    policy: DeletionPolicyName = Query("reparent"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> None:
    await _policy_for(policy, session).apply(employee_id, actor_id=principal.id)
    await session.commit()


@router.post("/{employee_id}/restore", response_model=EmployeeReadAny)
async def restore_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
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
    principal: Principal = Depends(require_role("hr_admin")),
) -> list[EmployeeReadAny]:
    affected = await preview(employee_id, _policy_for(policy, session))
    return [to_employee_read(e, principal) for e in affected]


@router.put("/{employee_id}/manager", response_model=EmployeeReadAny)
async def reassign_manager(
    employee_id: uuid.UUID,
    body: ManagerReassignRequest,
    if_match: str = Header(..., alias="If-Match"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
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
    principal: Principal = Depends(get_current_principal),
) -> AuditLogPage:
    repo = EmployeeRepository(session)
    if await repo.get_any(employee_id) is None:
        raise EmployeeNotFound(employee_id)

    audit = AuditService(session)
    rows, total = await audit.list_for_employee(
        employee_id, page=pagination.page, page_size=pagination.page_size
    )

    manager_ids = {
        uuid.UUID(snapshot["manager_id"])
        for row in rows
        if row.entry.action == "employee.reassigned"
        for snapshot in (row.entry.before, row.entry.after)
        if snapshot is not None and snapshot.get("manager_id") is not None
    }
    manager_names = await repo.get_names_by_ids(list(manager_ids))

    return AuditLogPage(
        items=[to_audit_log_read(row, principal, manager_names) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
