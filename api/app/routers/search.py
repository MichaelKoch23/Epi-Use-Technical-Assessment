from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.avatars import resolve_avatar_url
from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.search import SearchResultRead

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=list[SearchResultRead])
async def search(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[SearchResultRead]:
    repo = EmployeeRepository(session)
    employees = await repo.search(q)
    return [
        SearchResultRead(
            id=employee.id,
            first_name=employee.first_name,
            last_name=employee.last_name,
            position=employee.position,
            employee_number=employee.employee_number,
            avatar_url=resolve_avatar_url(
                avatar_override_url=employee.avatar_override_url, email=employee.email
            ),
        )
        for employee in employees
    ]
