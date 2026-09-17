from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, Query

from app.repositories.employee_repository import SORTABLE_COLUMNS, EmployeeListFilters


def as_of_param(
    as_of: date | None = Query(
        None, description="View the organisation as at this date (default: today)"
    ),
) -> date:
    """Resolve the as-of date once, so every handler echoes the same value back."""
    return as_of or datetime.now(UTC).date()


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    page_size: int


def page_params(
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(50, ge=1, le=500),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


@dataclass(frozen=True, slots=True)
class EmployeeSortParams:
    sort: str
    order: Literal["asc", "desc"]


def employee_sort_params(
    sort: str = Query(
        "last_name", description=f"One of: {', '.join(sorted(SORTABLE_COLUMNS))}"
    ),
    order: Literal["asc", "desc"] = Query("asc"),
) -> EmployeeSortParams:
    if sort not in SORTABLE_COLUMNS:
        raise HTTPException(status_code=422, detail=f"unsupported sort field: {sort!r}")
    return EmployeeSortParams(sort=sort, order=order)


def employee_filter_params(
    q: str | None = Query(None, description="Fuzzy match on first + last name"),
    position: str | None = Query(None),
    manager_id: uuid.UUID | None = Query(None),
    min_salary: Decimal | None = Query(None, ge=0),
    max_salary: Decimal | None = Query(None, ge=0),
    min_birth_date: date | None = Query(None),
    max_birth_date: date | None = Query(None),
    deleted: bool = Query(
        False, description="List soft-deleted employees instead of active ones"
    ),
) -> EmployeeListFilters:
    return EmployeeListFilters(
        q=q,
        position=position,
        manager_id=manager_id,
        min_salary=min_salary,
        max_salary=max_salary,
        min_birth_date=min_birth_date,
        max_birth_date=max_birth_date,
        deleted=deleted,
    )
