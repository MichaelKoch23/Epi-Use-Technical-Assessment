from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import (
    EmployeeSortParams,
    employee_filter_params,
    employee_sort_params,
)
from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.repositories.employee_repository import EmployeeListFilters, EmployeeRepository
from app.routers.employees import require_salary_access

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_BASE_COLUMNS = [
    "employee_number",
    "first_name",
    "last_name",
    "email",
    "birth_date",
    "position",
    "currency",
    "manager_employee_number",
]
_EXPORT_PAGE_SIZE = 500


def _csv_safe(value: str) -> str:
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


@router.get("/employees.csv")
async def export_employees_csv(
    filters: EmployeeListFilters = Depends(employee_filter_params),
    sort_params: EmployeeSortParams = Depends(employee_sort_params),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> StreamingResponse:
    require_salary_access(principal, filters, sort_params.sort)

    repo = EmployeeRepository(session)

    columns = [*_BASE_COLUMNS]
    if principal.is_admin:
        columns.insert(_BASE_COLUMNS.index("currency"), "salary")

    identity_map = await repo.list_active_identity_map()
    number_by_id = {emp_id: number for emp_id, number, _ in identity_map}

    async def rows() -> AsyncIterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        page = 1
        while True:
            items, total = await repo.list(
                filters,
                sort=sort_params.sort,
                order=sort_params.order,
                page=page,
                page_size=_EXPORT_PAGE_SIZE,
            )
            if not items:
                break
            for list_row in items:
                employee = list_row.employee
                values = {
                    "employee_number": employee.employee_number,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "email": employee.email,
                    "birth_date": employee.birth_date.isoformat(),
                    "position": employee.position,
                    "currency": employee.currency,
                    "manager_employee_number": (
                        number_by_id.get(employee.manager_id, "")
                        if employee.manager_id
                        else ""
                    ),
                    "salary": str(employee.salary),
                }
                writer.writerow([_csv_safe(values[c]) for c in columns])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            if page * _EXPORT_PAGE_SIZE >= total:
                break
            page += 1

    headers = {"Content-Disposition": 'attachment; filename="employees.csv"'}
    return StreamingResponse(rows(), media_type="text/csv", headers=headers)
