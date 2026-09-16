"""`/api/v1/hierarchy/*` - top-of-forest queries that don't belong to any
single employee. Per-employee hierarchy reads (`subtree`, `reporting-line`)
stay on the `employees` router (§6.2); this router is only for the roots
the org chart starts its initial fetch from."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.repositories.employee_repository import EmployeeRepository
from app.routers.employees import to_employee_read
from app.schemas.employee import EmployeeReadAny

router = APIRouter(prefix="/api/v1/hierarchy", tags=["hierarchy"])


@router.get("/roots", response_model=list[EmployeeReadAny])
async def get_roots(
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[EmployeeReadAny]:
    """Employees with no manager - the org chart's forest of starting
    points (there's no single-root guarantee, §15 known limitations)."""
    repo = EmployeeRepository(session)
    roots = await repo.get_roots()
    return [to_employee_read(e, principal) for e in roots]
