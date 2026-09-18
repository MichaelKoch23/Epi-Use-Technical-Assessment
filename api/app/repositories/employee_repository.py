from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import ColumnElement, case, func, or_, select, text
from sqlalchemy.engine import Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased

from app.models.employee import Employee

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
    deleted: bool = False


@dataclass(frozen=True, slots=True)
class EmployeeListRow:
    employee: Employee
    manager_name: str | None
    direct_report_count: int


@dataclass(frozen=True, slots=True)
class ManagerOptionRow:
    id: uuid.UUID
    first_name: str
    last_name: str
    employee_number: str


@dataclass(frozen=True, slots=True)
class EmployeeHierarchyRow:
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
          AND NOT c.id = ANY(s.path)
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

_IS_DESCENDANT_SQL = text(
    """
    WITH RECURSIVE subtree AS (
        SELECT id, 0 AS depth, ARRAY[id] AS path
        FROM employee WHERE id = :of_id
      UNION ALL
        SELECT c.id, s.depth + 1, s.path || c.id
        FROM employee c JOIN subtree s ON c.manager_id = s.id
        WHERE NOT c.id = ANY(s.path)
          AND s.depth < :max_depth
    )
    SELECT EXISTS (SELECT 1 FROM subtree WHERE id = :candidate_id) AS is_descendant
    """
)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_EMPLOYEE_COLUMNS = tuple(c.name for c in Employee.__table__.columns)


def _row_to_employee(row: RowMapping) -> Employee:
    employee = Employee()
    for column in _EMPLOYEE_COLUMNS:
        setattr(employee, column, row[column])
    return employee


def filter_conditions(filters: EmployeeListFilters) -> list[ColumnElement[bool]]:
    """The WHERE terms for a filtered employee query.

    Shared so that anything answering a question *about* a filtered set - the
    page itself, and the managers those people report to - is answering it about
    the same set. Two copies of this would drift the first time a filter is added.
    """
    conditions: list[ColumnElement[bool]] = [
        Employee.deleted_at.is_not(None)
        if filters.deleted
        else Employee.deleted_at.is_(None)
    ]
    if filters.q:
        full_name = func.concat(Employee.first_name, " ", Employee.last_name)
        conditions.append(full_name.ilike(f"%{_escape_like(filters.q)}%", escape="\\"))
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
    return conditions


class EmployeeRepository:
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

    async def get_by_email(self, email: str) -> Employee | None:
        stmt = select(Employee).where(
            func.lower(Employee.email) == email.lower(), Employee.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_any(self, id: uuid.UUID) -> Employee | None:
        stmt = select(Employee).where(Employee.id == id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_for_update(self, id: uuid.UUID) -> Employee | None:
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

        conditions = filter_conditions(filters)

        sort_column = SORTABLE_COLUMNS[sort]
        order_by = sort_column.asc() if order == "asc" else sort_column.desc()

        manager = aliased(Employee)
        report = aliased(Employee)
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
            select(Employee, manager_name, report_count, func.count().over())
            .outerjoin(manager, Employee.manager_id == manager.id)
            .where(*conditions)
            .order_by(order_by, Employee.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(list_stmt)).all()
        if rows:
            total = rows[0][3]
        elif page == 1:
            total = 0
        else:
            count_stmt = select(func.count()).select_from(Employee).where(*conditions)
            total = (await self._session.execute(count_stmt)).scalar_one()
        items = [
            EmployeeListRow(
                employee=employee, manager_name=manager_name_, direct_report_count=count
            )
            for employee, manager_name_, count, _ in rows
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
                _IS_DESCENDANT_SQL,
                {
                    "candidate_id": candidate_id,
                    "of_id": of_id,
                    "max_depth": MAX_REPORTING_DEPTH,
                },
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

    async def get_names_by_ids(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        stmt = select(Employee.id, Employee.first_name, Employee.last_name).where(
            Employee.id.in_(ids)
        )
        rows = (await self._session.execute(stmt)).all()
        return {id_: f"{first} {last}" for id_, first, last in rows}

    async def list_active_identity_map(
        self,
    ) -> Sequence[tuple[uuid.UUID, str, uuid.UUID | None]]:
        stmt = select(Employee.id, Employee.employee_number, Employee.manager_id).where(
            Employee.deleted_at.is_(None)
        )
        return [tuple(row) for row in (await self._session.execute(stmt)).all()]

    async def email_owners(self) -> dict[str, str]:
        stmt = select(Employee.email, Employee.employee_number).where(
            Employee.deleted_at.is_(None)
        )
        rows = (await self._session.execute(stmt)).all()
        return {email.lower(): number for email, number in rows}

    async def get_many_by_employee_numbers(
        self, employee_numbers: Collection[str]
    ) -> dict[str, Employee]:
        if not employee_numbers:
            return {}
        stmt = select(Employee).where(
            Employee.employee_number.in_(employee_numbers),
            Employee.deleted_at.is_(None),
        )
        return {
            e.employee_number: e for e in (await self._session.execute(stmt)).scalars()
        }

    async def count_reports(self, id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Employee)
            .where(Employee.manager_id == id, Employee.deleted_at.is_(None))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def list_managers(
        self, filters: EmployeeListFilters, *, limit: int = 100
    ) -> Sequence[ManagerOptionRow]:
        """The distinct managers that a filtered set of employees reports to.

        The manager filter itself is ignored: the caller is choosing what to set
        it to, so narrowing the candidates by the current choice would leave them
        with only the option they already have.
        """
        subject_filters = replace(filters, manager_id=None)
        manager = aliased(Employee)
        stmt = (
            select(
                manager.id,
                manager.first_name,
                manager.last_name,
                manager.employee_number,
            )
            .select_from(Employee)
            .join(manager, Employee.manager_id == manager.id)
            .where(*filter_conditions(subject_filters), manager.deleted_at.is_(None))
            .distinct()
            .order_by(manager.last_name, manager.first_name)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ManagerOptionRow(
                id=id_,
                first_name=first_name,
                last_name=last_name,
                employee_number=employee_number,
            )
            for id_, first_name, last_name, employee_number in rows
        ]

    async def list_positions(self) -> Sequence[str]:
        stmt = (
            select(Employee.position)
            .where(Employee.deleted_at.is_(None))
            .distinct()
            .order_by(Employee.position)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def search(self, q: str, *, limit: int = 8) -> Sequence[Employee]:
        pattern = f"%{_escape_like(q)}%"
        full_name = func.concat(Employee.first_name, " ", Employee.last_name)
        stmt = (
            select(Employee)
            .where(
                Employee.deleted_at.is_(None),
                or_(
                    full_name.ilike(pattern, escape="\\"),
                    Employee.employee_number.ilike(pattern, escape="\\"),
                    Employee.position.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(Employee.last_name)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()
