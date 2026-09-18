from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.engine import Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_assignment import EmployeeAssignment
from app.repositories.employee_repository import MAX_REPORTING_DEPTH

_EDGE_CTE = """
    edge AS (
        SELECT a.employee_id, a.manager_id
        FROM employee_assignment a
        WHERE a.valid_from <= :as_of
          AND (a.valid_to IS NULL OR a.valid_to > :as_of)
    )
"""


def _alive(alias: str) -> str:
    """Employees who had not yet been deleted as at :as_of.

    A departure ends on its date the same way a reporting edge does: deleting
    someone on the 18th removes them from the 18th onward and leaves the 17th
    untouched. Hence the cast to date - deleted_at is a timestamp, and
    comparing it raw against :as_of would put anyone deleted later in the day
    back into their own last day's chart.

    Arrivals are deliberately not dated. There is no hire date on the employee
    row, and created_at records when the row was written rather than when the
    person joined, so a historical view shows today's joiners as though they
    had always been there (TECHNICAL-DESIGN section 4.3).
    """
    return f"({alias}.deleted_at IS NULL OR {alias}.deleted_at::date > :as_of)"


_TREE_SQL = text(
    f"""
    WITH RECURSIVE {_EDGE_CTE},
    tree AS (
        -- Roots as at the date: nobody above them, or nobody above them any
        -- more. Deleting a manager reparents their reports from that day on
        -- (see DeletionPolicy), so the second case should not arise on data
        -- this application wrote. It is kept as a guard: an edge left pointing
        -- at someone already gone by :as_of would otherwise strand their whole
        -- branch outside the tree, and empty the view entirely when that
        -- manager was the only root.
        SELECT e.id, NULL::uuid AS manager_id, 0 AS depth, ARRAY[e.id] AS path
        FROM employee e
        LEFT JOIN edge ed ON ed.employee_id = e.id
        LEFT JOIN employee m ON m.id = ed.manager_id AND {_alive("m")}
        WHERE {_alive("e")}
          AND m.id IS NULL
      UNION ALL
        SELECT c.id, ed.manager_id, t.depth + 1, t.path || c.id
        FROM edge ed
        JOIN employee c ON c.id = ed.employee_id AND {_alive("c")}
        JOIN tree   t   ON ed.manager_id = t.id
        WHERE NOT c.id = ANY(t.path)
          AND t.depth < :max_depth
    )
    SELECT e.*, tree.manager_id AS as_of_manager_id, tree.depth
    FROM tree
    JOIN employee e ON e.id = tree.id
    ORDER BY tree.depth, e.last_name, e.first_name
    """
)

_SUBTREE_SQL = text(
    f"""
    WITH RECURSIVE {_EDGE_CTE},
    tree AS (
        SELECT e.id, ed.manager_id, 0 AS depth, ARRAY[e.id] AS path
        FROM employee e
        LEFT JOIN edge ed ON ed.employee_id = e.id
        WHERE e.id = :root_id AND {_alive("e")}
      UNION ALL
        SELECT c.id, ed.manager_id, t.depth + 1, t.path || c.id
        FROM edge ed
        JOIN employee c ON c.id = ed.employee_id AND {_alive("c")}
        JOIN tree   t   ON ed.manager_id = t.id
        WHERE NOT c.id = ANY(t.path)
          AND t.depth < :max_depth
    )
    SELECT e.*, tree.manager_id AS as_of_manager_id, tree.depth
    FROM tree
    JOIN employee e ON e.id = tree.id
    ORDER BY tree.depth, e.last_name, e.first_name
    """
)

_ANCESTORS_SQL = text(
    f"""
    WITH RECURSIVE {_EDGE_CTE},
    line AS (
        SELECT e.id, ed.manager_id, 0 AS level, ARRAY[e.id] AS path
        FROM employee e
        LEFT JOIN edge ed ON ed.employee_id = e.id
        WHERE e.id = :employee_id AND {_alive("e")}
      UNION ALL
        SELECT m.id, ed.manager_id, l.level + 1, l.path || m.id
        FROM line l
        JOIN employee m ON m.id = l.manager_id AND {_alive("m")}
        LEFT JOIN edge ed ON ed.employee_id = m.id
        WHERE l.level < :max_depth
          AND NOT m.id = ANY(l.path)
    )
    SELECT e.*, line.manager_id AS as_of_manager_id, line.level AS depth
    FROM line
    JOIN employee e ON e.id = line.id
    WHERE line.level > 0
    ORDER BY line.level
    """
)

_IS_DESCENDANT_SQL = text(
    f"""
    WITH RECURSIVE {_EDGE_CTE},
    subtree AS (
        SELECT CAST(:of_id AS uuid) AS id, 0 AS depth,
               ARRAY[CAST(:of_id AS uuid)] AS path
      UNION ALL
        SELECT ed.employee_id, s.depth + 1, s.path || ed.employee_id
        FROM edge ed
        JOIN subtree s ON ed.manager_id = s.id
        WHERE NOT ed.employee_id = ANY(s.path)
          AND s.depth < :max_depth
    )
    SELECT EXISTS (SELECT 1 FROM subtree WHERE id = :candidate_id) AS is_descendant
    """
)

_EDGES_AT_SQL = text(
    f"""
    WITH {_EDGE_CTE}
    SELECT e.id, edge.manager_id
    FROM employee e
    LEFT JOIN edge ON edge.employee_id = e.id
    WHERE {_alive("e")}
    """
)

_BOUNDARY_DATES_SQL = text(
    """
    SELECT DISTINCT d
    FROM (
        SELECT valid_from AS d FROM employee_assignment WHERE valid_from > :after
        UNION
        SELECT valid_to   AS d FROM employee_assignment WHERE valid_to   > :after
    ) boundaries
    WHERE d IS NOT NULL
    ORDER BY d
    """
)

_SUBTREE_SALARY_SQL = text(
    f"""
    WITH RECURSIVE {_EDGE_CTE},
    tree AS (
        SELECT e.id, ARRAY[e.id] AS path
        FROM employee e
        WHERE e.id = :root_id AND {_alive("e")}
      UNION ALL
        SELECT c.id, t.path || c.id
        FROM edge ed
        JOIN employee c ON c.id = ed.employee_id AND {_alive("c")}
        JOIN tree   t   ON ed.manager_id = t.id
        WHERE NOT c.id = ANY(t.path)
    )
    SELECT count(*) AS headcount,
           coalesce(sum(e.salary), 0) AS total_annual,
           min(e.currency) AS currency
    FROM tree
    JOIN employee e ON e.id = tree.id
    """
)

_SYNCED_KEY = "assignments_synced"

_EMPLOYEE_COLUMNS = tuple(c.name for c in Employee.__table__.columns)


def _row_to_employee(row: RowMapping) -> Employee:
    """Build an Employee whose manager_id is the edge at :as_of, not the cache.

    employee.manager_id is only ever correct for today. Overwriting it with the
    as-of edge is what stops a historical view from quietly rendering present-day
    relationships.
    """
    employee = Employee()
    for column in _EMPLOYEE_COLUMNS:
        setattr(employee, column, row[column])
    employee.manager_id = row["as_of_manager_id"]
    return employee


@dataclass(frozen=True, slots=True)
class AssignmentHierarchyRow:
    employee: Employee
    depth: int


@dataclass(frozen=True, slots=True)
class AssignmentHistoryRow:
    assignment: EmployeeAssignment
    manager_name: str | None
    created_by_email: str | None


@dataclass(frozen=True, slots=True)
class ScheduledAssignmentRow:
    assignment: EmployeeAssignment
    employee_name: str
    employee_position: str
    manager_name: str | None
    created_by_email: str | None


@dataclass(frozen=True, slots=True)
class SubtreeCost:
    headcount: int
    total_annual: Any
    currency: str


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sync_effective(self, *, force: bool = False) -> int:
        """Recompute employee.manager_id from whatever is effective today.

        Returns the number of rows the cache was out by - zero on almost every
        call, which is the point. Sessions here are request-scoped, so the first
        call in a session covers the whole write transaction and later ones are
        skipped; a bulk import does not pay for this once per row. `force` is for
        the one caller that needs the cache refreshed mid-transaction: a
        reassignment taking effect today.
        """
        if not force and self._session.info.get(_SYNCED_KEY):
            return 0
        result = await self._session.execute(
            text("SELECT sync_effective_assignments() AS touched")
        )
        self._session.info[_SYNCED_KEY] = True
        return int(result.scalar_one())

    async def get_tree(
        self,
        as_of: date,
        *,
        root_id: uuid.UUID | None = None,
        max_depth: int | None = None,
    ) -> Sequence[AssignmentHierarchyRow]:
        if root_id is not None:
            return await self.get_subtree(root_id, as_of, max_depth=max_depth)
        result = await self._session.execute(
            _TREE_SQL,
            {
                "as_of": as_of,
                "max_depth": MAX_REPORTING_DEPTH if max_depth is None else max_depth,
            },
        )
        return [
            AssignmentHierarchyRow(employee=_row_to_employee(row), depth=row["depth"])
            for row in result.mappings()
        ]

    async def get_subtree(
        self,
        employee_id: uuid.UUID,
        as_of: date,
        *,
        max_depth: int | None = None,
    ) -> Sequence[AssignmentHierarchyRow]:
        result = await self._session.execute(
            _SUBTREE_SQL,
            {
                "as_of": as_of,
                "root_id": employee_id,
                "max_depth": MAX_REPORTING_DEPTH if max_depth is None else max_depth,
            },
        )
        return [
            AssignmentHierarchyRow(employee=_row_to_employee(row), depth=row["depth"])
            for row in result.mappings()
        ]

    async def get_ancestors(
        self, employee_id: uuid.UUID, as_of: date
    ) -> Sequence[AssignmentHierarchyRow]:
        result = await self._session.execute(
            _ANCESTORS_SQL,
            {
                "as_of": as_of,
                "employee_id": employee_id,
                "max_depth": MAX_REPORTING_DEPTH,
            },
        )
        return [
            AssignmentHierarchyRow(employee=_row_to_employee(row), depth=row["depth"])
            for row in result.mappings()
        ]

    async def is_descendant(
        self, candidate_id: uuid.UUID, of_id: uuid.UUID, as_of: date
    ) -> bool:
        row: Row[Any] = (
            await self._session.execute(
                _IS_DESCENDANT_SQL,
                {
                    "as_of": as_of,
                    "candidate_id": candidate_id,
                    "of_id": of_id,
                    "max_depth": MAX_REPORTING_DEPTH,
                },
            )
        ).one()
        return bool(row.is_descendant)

    async def get_edges_at(self, as_of: date) -> dict[uuid.UUID, uuid.UUID | None]:
        result = await self._session.execute(_EDGES_AT_SQL, {"as_of": as_of})
        return {row.id: row.manager_id for row in result}

    async def get_assignment_history(
        self, employee_id: uuid.UUID
    ) -> Sequence[AssignmentHistoryRow]:
        stmt = text(
            """
            SELECT a.*,
                   CASE WHEN m.id IS NULL THEN NULL
                        ELSE m.first_name || ' ' || m.last_name END AS manager_name,
                   u.email AS created_by_email
            FROM employee_assignment a
            LEFT JOIN employee m ON m.id = a.manager_id
            LEFT JOIN app_user u ON u.id = a.created_by
            WHERE a.employee_id = :employee_id
            ORDER BY a.valid_from DESC, a.created_at DESC
            """
        )
        result = await self._session.execute(stmt, {"employee_id": employee_id})
        return [
            AssignmentHistoryRow(
                assignment=_row_to_assignment(row),
                manager_name=row["manager_name"],
                created_by_email=row["created_by_email"],
            )
            for row in result.mappings()
        ]

    async def get_scheduled(
        self, after: date | None = None
    ) -> Sequence[ScheduledAssignmentRow]:
        stmt = text(
            """
            SELECT a.*,
                   e.first_name || ' ' || e.last_name AS employee_name,
                   e.position AS employee_position,
                   CASE WHEN m.id IS NULL THEN NULL
                        ELSE m.first_name || ' ' || m.last_name END AS manager_name,
                   u.email AS created_by_email
            FROM employee_assignment a
            JOIN employee e ON e.id = a.employee_id AND e.deleted_at IS NULL
            LEFT JOIN employee m ON m.id = a.manager_id
            LEFT JOIN app_user u ON u.id = a.created_by
            WHERE a.valid_from > coalesce(:after, CURRENT_DATE)
            ORDER BY a.valid_from, e.last_name, e.first_name
            """
        )
        result = await self._session.execute(stmt, {"after": after})
        return [
            ScheduledAssignmentRow(
                assignment=_row_to_assignment(row),
                employee_name=row["employee_name"],
                employee_position=row["employee_position"],
                manager_name=row["manager_name"],
                created_by_email=row["created_by_email"],
            )
            for row in result.mappings()
        ]

    async def get_boundary_dates(self, after: date) -> list[date]:
        result = await self._session.execute(_BOUNDARY_DATES_SQL, {"after": after})
        return [row.d for row in result]

    async def get_subtree_cost(
        self, employee_id: uuid.UUID, as_of: date
    ) -> SubtreeCost:
        row = (
            await self._session.execute(
                _SUBTREE_SALARY_SQL, {"as_of": as_of, "root_id": employee_id}
            )
        ).one()
        return SubtreeCost(
            headcount=row.headcount,
            total_annual=row.total_annual,
            currency=row.currency or "ZAR",
        )

    async def get_salary_total(
        self, employee_ids: Sequence[uuid.UUID]
    ) -> tuple[Decimal, str]:
        if not employee_ids:
            return Decimal(0), "ZAR"
        stmt = select(
            func.coalesce(func.sum(Employee.salary), 0),
            func.coalesce(func.min(Employee.currency), "ZAR"),
        ).where(Employee.id.in_(employee_ids), Employee.deleted_at.is_(None))
        total, currency = (await self._session.execute(stmt)).one()
        return Decimal(total), currency

    async def get(self, assignment_id: uuid.UUID) -> EmployeeAssignment | None:
        stmt = select(EmployeeAssignment).where(EmployeeAssignment.id == assignment_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_open_at(
        self, employee_id: uuid.UUID, as_of: date
    ) -> EmployeeAssignment | None:
        """The assignment in force for an employee on a given day, if any."""
        stmt = (
            select(EmployeeAssignment)
            .where(
                EmployeeAssignment.employee_id == employee_id,
                EmployeeAssignment.valid_from <= as_of,
                (EmployeeAssignment.valid_to.is_(None))
                | (EmployeeAssignment.valid_to > as_of),
            )
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_starting_on_or_after(
        self, employee_id: uuid.UUID, start: date, *, for_update: bool = True
    ) -> Sequence[EmployeeAssignment]:
        """Assignments beginning on or after a date.

        Locked by default, because the caller that matters is set_edge, which is
        about to delete these rows. A caller that only wants to *show* them must
        pass for_update=False: move-preview is open to every signed-in viewer,
        and taking write locks to render a preview would let any reader stall an
        administrator's reassignment for the length of a request.
        """
        stmt = (
            select(EmployeeAssignment)
            .where(
                EmployeeAssignment.employee_id == employee_id,
                EmployeeAssignment.valid_from >= start,
            )
            .order_by(EmployeeAssignment.valid_from)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalars().all()

    async def get_earliest_valid_from(self, employee_id: uuid.UUID) -> date | None:
        stmt = select(func.min(EmployeeAssignment.valid_from)).where(
            EmployeeAssignment.employee_id == employee_id
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def get_preceding(
        self, employee_id: uuid.UUID, valid_from: date
    ) -> EmployeeAssignment | None:
        """The assignment a scheduled one was going to supersede."""
        stmt = (
            select(EmployeeAssignment)
            .where(
                EmployeeAssignment.employee_id == employee_id,
                EmployeeAssignment.valid_to == valid_from,
            )
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalars().first()

    def add(self, assignment: EmployeeAssignment) -> None:
        self._session.add(assignment)

    async def delete(self, assignment: EmployeeAssignment) -> None:
        await self._session.delete(assignment)

    async def set_edge(
        self,
        employee_id: uuid.UUID,
        manager_id: uuid.UUID | None,
        *,
        effective_from: date,
        reason: str | None,
        created_by: uuid.UUID | None,
    ) -> tuple[EmployeeAssignment, list[EmployeeAssignment]]:
        """Make `manager_id` the employee's manager from `effective_from` on.

        The mechanical half of a reassignment, with no validation and no audit:
        close the run in force, drop anything scheduled from this date onward,
        open a new run. Returns the new assignment and the rows it superseded.
        Every write path that changes a reporting edge goes through here, which
        is what keeps employee_assignment complete rather than only recording
        moves made through the effective-dating endpoints.
        """
        superseded = list(
            await self.get_starting_on_or_after(employee_id, effective_from)
        )
        open_row = await self.get_open_at(employee_id, effective_from)
        for row in superseded:
            await self.delete(row)
        if open_row is not None and open_row.valid_from < effective_from:
            open_row.valid_to = effective_from
        await self._session.flush()

        assignment = EmployeeAssignment(
            employee_id=employee_id,
            manager_id=manager_id,
            valid_from=effective_from,
            valid_to=None,
            reason=reason,
            created_by=created_by,
        )
        self._session.add(assignment)
        await self._session.flush()
        return assignment, superseded


_ASSIGNMENT_COLUMNS = tuple(c.name for c in EmployeeAssignment.__table__.columns)


def _row_to_assignment(row: RowMapping) -> EmployeeAssignment:
    assignment = EmployeeAssignment()
    for column in _ASSIGNMENT_COLUMNS:
        setattr(assignment, column, row[column])
    return assignment
