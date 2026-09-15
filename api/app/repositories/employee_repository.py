from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import ColumnElement, case, func, select, text
from sqlalchemy.engine import Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased

from app.models.employee import Employee

# §6.3: sort is resolved against a static allow-list, never built from raw
# user input — dynamic ORDER BY is the classic injection vector that bound
# parameters don't protect against, because identifiers can't be bound.
SORTABLE_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
    "employee_number": Employee.employee_number,
    "first_name": Employee.first_name,
    "last_name": Employee.last_name,
    "email": Employee.email,
    "birth_date": Employee.birth_date,
    "position": Employee.position,
    "salary": Employee.salary,
    "created_at": Employee.created_at,
    "updated_at": Employee.updated_at,
}

# §5.2: the reporting chain is walked with a hop counter as a defensive cap,
# independent of any corrupt data the path guard would already have stopped.
MAX_REPORTING_DEPTH = 1000


@dataclass(frozen=True, slots=True)
class EmployeeListFilters:
    q: str | None = None
    position: str | None = None
    manager_id: uuid.UUID | None = None
    min_salary: Decimal | None = None
    max_salary: Decimal | None = None
    min_birth_date: date | None = None
    max_birth_date: date | None = None


@dataclass(frozen=True, slots=True)
class EmployeeListRow:
    """One row of a paged list: the employee plus fields that would
    otherwise cost an extra query per row — the manager's display name and
    direct-report count, both computed in the same statement (§below)."""

    employee: Employee
    manager_name: str | None
    direct_report_count: int


@dataclass(frozen=True, slots=True)
class EmployeeHierarchyRow:
    """One row of a subtree or ancestor-chain walk: the employee plus its
    distance (in hops) from the query's root."""

    employee: Employee
    depth: int


_SUBTREE_SQL = text(
    """
    WITH RECURSIVE subtree AS (
        SELECT e.*, 0 AS depth, ARRAY[e.id] AS path
        FROM employee e
        WHERE e.id = :root_id AND e.deleted_at IS NULL
      UNION ALL
        SELECT c.*, s.depth + 1, s.path || c.id
        FROM employee c
        JOIN subtree s ON c.manager_id = s.id
        WHERE c.deleted_at IS NULL
          AND NOT c.id = ANY(s.path)          -- terminates even on corrupt data
          AND s.depth < :max_depth
    )
    SELECT * FROM subtree ORDER BY depth, last_name
    """
)

_ANCESTORS_SQL = text(
    """
    WITH RECURSIVE line AS (
        SELECT e.id, e.manager_id, 0 AS level
        FROM employee e
        WHERE e.id = :employee_id AND e.deleted_at IS NULL
      UNION ALL
        SELECT m.id, m.manager_id, l.level + 1
        FROM employee m
        JOIN line l ON m.id = l.manager_id
        WHERE m.deleted_at IS NULL AND l.level < :max_level
    )
    SELECT e.*, line.level AS depth
    FROM line
    JOIN employee e ON e.id = line.id
    WHERE line.level > 0
    ORDER BY line.level
    """
)

# The proposed manager must not already be inside the employee's own
# subtree — walking down from `of_id` and testing whether `candidate_id`
# is reachable. This is the pre-write half of cycle prevention; the
# deferred constraint trigger (§5.2) is the authority that closes the
# concurrency race this check alone cannot.
_IS_DESCENDANT_SQL = text(
    """
    WITH RECURSIVE subtree AS (
        SELECT id FROM employee WHERE id = :of_id
      UNION ALL
        SELECT c.id FROM employee c JOIN subtree s ON c.manager_id = s.id
    )
    SELECT EXISTS (SELECT 1 FROM subtree WHERE id = :candidate_id) AS is_descendant
    """
)

# Columns of `employee` in the order SELECT * returns them — used to hydrate
# a detached Employee instance from a raw CTE row without touching the
# session's identity map (these rows carry extra columns the ORM doesn't
# know about, so a plain `select(Employee)` can't be used here).
_EMPLOYEE_COLUMNS = tuple(c.name for c in Employee.__table__.columns)


def _row_to_employee(row: RowMapping) -> Employee:
    employee = Employee()
    for column in _EMPLOYEE_COLUMNS:
        setattr(employee, column, row[column])
    return employee


class EmployeeRepository:
    """Query construction for the `employee` table. Enforces no business
    rules of its own — that's the service layer's job (§3.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: uuid.UUID) -> Employee | None:
        stmt = select(Employee).where(Employee.id == id, Employee.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_employee_number(self, employee_number: str) -> Employee | None:
        stmt = select(Employee).where(
            Employee.employee_number == employee_number, Employee.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_any(self, id: uuid.UUID) -> Employee | None:
        """Like `get`, but also returns soft-deleted rows — used by restore."""
        stmt = select(Employee).where(Employee.id == id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_for_update(self, id: uuid.UUID) -> Employee | None:
        """Row-locking read for the services that mutate the hierarchy
        (§5.2): `SELECT ... FOR UPDATE`, serialising conflicting writes to
        the same row regardless of which app instance handles them."""
        stmt = (
            select(Employee)
            .where(Employee.id == id, Employee.deleted_at.is_(None))
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        filters: EmployeeListFilters,
        *,
        sort: str = "last_name",
        order: Literal["asc", "desc"] = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[EmployeeListRow], int]:
        if sort not in SORTABLE_COLUMNS:
            raise ValueError(f"unsupported sort field: {sort!r}")
        if page < 1:
            raise ValueError("page must be >= 1")
        if not (1 <= page_size <= 500):
            raise ValueError("page_size must be between 1 and 500")

        conditions: list[ColumnElement[bool]] = [Employee.deleted_at.is_(None)]
        if filters.q:
            full_name = func.concat(Employee.first_name, " ", Employee.last_name)
            conditions.append(full_name.ilike("%" + filters.q + "%"))
        if filters.position is not None:
            conditions.append(Employee.position == filters.position)
        if filters.manager_id is not None:
            conditions.append(Employee.manager_id == filters.manager_id)
        if filters.min_salary is not None:
            conditions.append(Employee.salary >= filters.min_salary)
        if filters.max_salary is not None:
            conditions.append(Employee.salary <= filters.max_salary)
        if filters.min_birth_date is not None:
            conditions.append(Employee.birth_date >= filters.min_birth_date)
        if filters.max_birth_date is not None:
            conditions.append(Employee.birth_date <= filters.max_birth_date)

        sort_column = SORTABLE_COLUMNS[sort]
        order_by = sort_column.asc() if order == "asc" else sort_column.desc()

        manager = aliased(Employee)
        report = aliased(Employee)
        # `concat()` (unlike `||`) treats NULL arguments as empty strings, so
        # a root employee's absent manager would otherwise come back as the
        # single-space string `" "` instead of NULL.
        manager_name = case(
            (manager.id.is_(None), None),
            else_=func.concat(manager.first_name, " ", manager.last_name),
        )
        report_count = (
            select(func.count())
            .select_from(report)
            .where(report.manager_id == Employee.id, report.deleted_at.is_(None))
            .correlate(Employee)
            .scalar_subquery()
        )

        list_stmt = (
            select(Employee, manager_name, report_count)
            .outerjoin(manager, Employee.manager_id == manager.id)
            .where(*conditions)
            .order_by(order_by, Employee.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        count_stmt = select(func.count()).select_from(Employee).where(*conditions)

        rows = (await self._session.execute(list_stmt)).all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        items = [
            EmployeeListRow(employee=employee, manager_name=manager_name_, direct_report_count=count)
            for employee, manager_name_, count in rows
        ]
        return items, total

    async def get_subtree(
        self, root_id: uuid.UUID, max_depth: int | None = None
    ) -> Sequence[EmployeeHierarchyRow]:
        depth_limit = MAX_REPORTING_DEPTH if max_depth is None else max_depth
        result = await self._session.execute(
            _SUBTREE_SQL, {"root_id": root_id, "max_depth": depth_limit}
        )
        return [
            EmployeeHierarchyRow(employee=_row_to_employee(row), depth=row["depth"])
            for row in result.mappings()
        ]

    async def get_ancestors(self, id: uuid.UUID) -> Sequence[EmployeeHierarchyRow]:
        result = await self._session.execute(
            _ANCESTORS_SQL, {"employee_id": id, "max_level": MAX_REPORTING_DEPTH}
        )
        return [
            EmployeeHierarchyRow(employee=_row_to_employee(row), depth=row["depth"])
            for row in result.mappings()
        ]

    async def is_descendant(self, candidate_id: uuid.UUID, of_id: uuid.UUID) -> bool:
        result: Row[Any] = (
            await self._session.execute(
                _IS_DESCENDANT_SQL, {"candidate_id": candidate_id, "of_id": of_id}
            )
        ).one()
        return bool(result.is_descendant)

    async def get_roots(self) -> Sequence[Employee]:
        stmt = select(Employee).where(
            Employee.manager_id.is_(None), Employee.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get_direct_reports(self, manager_id: uuid.UUID) -> Sequence[Employee]:
        stmt = select(Employee).where(
            Employee.manager_id == manager_id, Employee.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def count_reports(self, id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Employee)
            .where(Employee.manager_id == id, Employee.deleted_at.is_(None))
        )
        return (await self._session.execute(stmt)).scalar_one()
