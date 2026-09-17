from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import as_of_param
from app.core.security import Principal, get_current_principal, require_role
from app.db.session import get_db
from app.repositories.assignment_repository import (
    AssignmentRepository,
    ScheduledAssignmentRow,
)
from app.routers.employees import to_employee_read
from app.schemas.assignment import (
    AsOfEmployees,
    AsOfHierarchy,
    DiffCostRead,
    ManagerChangeRead,
    ScheduledAssignmentRead,
    ScheduledAssignmentsRead,
    StructureDiffRead,
    StructureDiffReadAny,
    StructureDiffReadRestricted,
)
from app.schemas.employee import EmployeeHierarchyNode
from app.services.assignment_service import (
    AssignmentService,
    ManagerChange,
    StructureDiff,
)
from app.services.assignment_service import today as today_date

router = APIRouter(prefix="/api/v1/hierarchy", tags=["hierarchy"])


def to_scheduled_read(row: ScheduledAssignmentRow) -> ScheduledAssignmentRead:
    a = row.assignment
    return ScheduledAssignmentRead(
        id=a.id,
        employee_id=a.employee_id,
        employee_name=row.employee_name,
        employee_position=row.employee_position,
        manager_id=a.manager_id,
        manager_name=row.manager_name,
        effective_from=a.valid_from,
        reason=a.reason,
        created_by_email=row.created_by_email,
        created_at=a.created_at,
    )


def _to_manager_change_read(change: ManagerChange) -> ManagerChangeRead:
    return ManagerChangeRead(
        employee_id=change.employee_id,
        employee_name=change.employee_name,
        from_manager_id=change.from_manager_id,
        from_manager_name=change.from_manager_name,
        to_manager_id=change.to_manager_id,
        to_manager_name=change.to_manager_name,
        subtree_size=change.subtree_size,
    )


def _to_structure_diff_read(
    diff: StructureDiff, principal: Principal
) -> StructureDiffReadAny:
    fields: dict[str, Any] = {
        "from_date": diff.from_date,
        "to_date": diff.to_date,
        "manager_changes": [_to_manager_change_read(c) for c in diff.manager_changes],
        "branch_moves": [_to_manager_change_read(c) for c in diff.branch_moves],
        "became_root": [_to_manager_change_read(c) for c in diff.became_root],
        "stopped_being_root": [
            _to_manager_change_read(c) for c in diff.stopped_being_root
        ],
        "max_depth_from": diff.max_depth_from,
        "max_depth_to": diff.max_depth_to,
        "max_depth_change": diff.max_depth_to - diff.max_depth_from,
        "average_span_from": diff.average_span_from,
        "average_span_to": diff.average_span_to,
        "average_span_change": round(diff.average_span_to - diff.average_span_from, 2),
    }
    if principal.is_admin:
        return StructureDiffRead(
            **fields,
            cost=DiffCostRead(total_moved=diff.moved_salary, currency=diff.currency),
        )
    return StructureDiffReadRestricted(**fields)


@router.get("/roots", response_model=AsOfEmployees)
async def get_roots(
    as_of: date = Depends(as_of_param),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> AsOfEmployees:
    rows = await AssignmentRepository(session).get_tree(as_of, max_depth=0)
    return AsOfEmployees(
        as_of=as_of,
        items=[to_employee_read(row.employee, principal) for row in rows],
    )


@router.get("/tree", response_model=AsOfHierarchy)
async def get_tree(
    as_of: date = Depends(as_of_param),
    root_id: uuid.UUID | None = Query(None),
    depth: int | None = Query(None, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> AsOfHierarchy:
    rows = await AssignmentRepository(session).get_tree(
        as_of, root_id=root_id, max_depth=depth
    )
    return AsOfHierarchy(
        as_of=as_of,
        items=[
            EmployeeHierarchyNode(
                employee=to_employee_read(row.employee, principal), depth=row.depth
            )
            for row in rows
        ],
    )


@router.get("/scheduled", response_model=ScheduledAssignmentsRead)
async def get_scheduled(
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(get_current_principal),
) -> ScheduledAssignmentsRead:
    rows = await AssignmentService(session).get_scheduled()
    return ScheduledAssignmentsRead(
        as_of=today_date(), items=[to_scheduled_read(row) for row in rows]
    )


@router.delete("/scheduled/{assignment_id}", status_code=204)
async def cancel_scheduled(
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> None:
    await AssignmentService(session).cancel_scheduled(
        assignment_id, actor_id=principal.id
    )
    await session.commit()


@router.get("/diff", response_model=StructureDiffReadAny)
async def get_structure_diff(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> StructureDiffReadAny:
    diff = await AssignmentService(session).diff_structure(from_date, to_date)
    return _to_structure_diff_read(diff, principal)
