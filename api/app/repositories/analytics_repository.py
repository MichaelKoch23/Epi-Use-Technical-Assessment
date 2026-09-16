from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.employee import Employee


@dataclass(frozen=True, slots=True)
class DepthRow:
    """One active employee's distance from the nearest root — the raw rows
    behind both `depth_distribution` (grouped by depth) and the deep-chain
    anomaly (filtered by depth), so a single walk of the tree serves both
    rather than running the recursive CTE twice."""

    id: uuid.UUID
    name: str
    position: str
    depth: int


@dataclass(frozen=True, slots=True)
class SpanRow:
    """One employee's direct-report count — the raw rows behind
    `span_distribution`, `manager_count`, `individual_contributor_count`,
    the span-of-control average/median, and the wide-span/single-report
    anomalies. `direct_reports` is 0 for an individual contributor, thanks
    to the `LEFT JOIN` in the query behind this."""

    id: uuid.UUID
    name: str
    position: str
    direct_reports: int


@dataclass(frozen=True, slots=True)
class UnreachableRow:
    id: uuid.UUID
    name: str
    position: str


@dataclass(frozen=True, slots=True)
class CostAggregate:
    headcount: int
    total_annual: Decimal
    average: Decimal
    median: Decimal


# Walks down from every root, tagging each active employee with its depth
# below the nearest root (§4.6) — the `NOT id = ANY(path)` guard terminates
# even on corrupt (cyclic) data, consistent with `_SUBTREE_SQL` in
# `employee_repository.py`. Employees unreachable from any root (see
# `_UNREACHABLE_SQL` below) simply never appear in these rows.
_DEPTH_WALK_SQL = text(
    """
    WITH RECURSIVE tree AS (
        SELECT e.id, e.first_name, e.last_name, e.position, 0 AS depth,
               ARRAY[e.id] AS path
        FROM employee e
        WHERE e.manager_id IS NULL AND e.deleted_at IS NULL
      UNION ALL
        SELECT c.id, c.first_name, c.last_name, c.position, t.depth + 1,
               t.path || c.id
        FROM employee c
        JOIN tree t ON c.manager_id = t.id
        WHERE c.deleted_at IS NULL AND NOT c.id = ANY(t.path)
    )
    SELECT id, first_name || ' ' || last_name AS name, position, depth
    FROM tree
    ORDER BY depth
    """
)

# Active employees that cannot be reached from any root — normally zero
# rows; a manager soft-deleted without its subtree being reparented is the
# only way this fires (§ data-integrity check).
_UNREACHABLE_SQL = text(
    """
    WITH RECURSIVE tree AS (
        SELECT e.id, ARRAY[e.id] AS path
        FROM employee e
        WHERE e.manager_id IS NULL AND e.deleted_at IS NULL
      UNION ALL
        SELECT c.id, t.path || c.id
        FROM employee c
        JOIN tree t ON c.manager_id = t.id
        WHERE c.deleted_at IS NULL AND NOT c.id = ANY(t.path)
    )
    SELECT e.id, e.first_name || ' ' || e.last_name AS name, e.position
    FROM employee e
    WHERE e.deleted_at IS NULL
      AND e.id NOT IN (SELECT id FROM tree)
    LIMIT :limit
    """
)


class AnalyticsRepository:
    """Query construction for the org-structure dashboard. Enforces no
    business rules of its own (thresholds, role gating) — that's
    `AnalyticsService`'s job (§3.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_depths(self) -> Sequence[DepthRow]:
        result = await self._session.execute(_DEPTH_WALK_SQL)
        return [DepthRow(**row) for row in result.mappings()]

    async def get_span_of_control(self) -> Sequence[SpanRow]:
        manager = aliased(Employee)
        report = aliased(Employee)
        stmt = (
            select(
                manager.id,
                func.concat(manager.first_name, " ", manager.last_name),
                manager.position,
                func.count(report.id),
            )
            .outerjoin(
                report,
                (report.manager_id == manager.id) & (report.deleted_at.is_(None)),
            )
            .where(manager.deleted_at.is_(None))
            .group_by(
                manager.id, manager.first_name, manager.last_name, manager.position
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            SpanRow(id=id_, name=name, position=position, direct_reports=count)
            for id_, name, position, count in rows
        ]

    async def get_unreachable(self, limit: int) -> Sequence[UnreachableRow]:
        result = await self._session.execute(_UNREACHABLE_SQL, {"limit": limit})
        return [UnreachableRow(**row) for row in result.mappings()]

    async def get_cost_aggregate(
        self, ids: Sequence[uuid.UUID] | None = None
    ) -> CostAggregate:
        """Admin-only aggregate (§9.3) — callers must not invoke this for a
        viewer at all, not merely hide the result. `ids=None` aggregates the
        whole organisation; otherwise it's scoped to a branch's subtree."""
        conditions = [Employee.deleted_at.is_(None)]
        if ids is not None:
            conditions.append(Employee.id.in_(ids))

        # `percentile_cont` returns `double precision` in Postgres — cast
        # back to `numeric` so the median comes back as a `Decimal`, never a
        # float, same as every other monetary value in this response.
        median_numeric = (
            func.percentile_cont(0.5)
            .within_group(Employee.salary)
            .cast(Employee.salary.type)
        )
        stmt = select(
            func.count(),
            func.coalesce(func.sum(Employee.salary), 0),
            func.coalesce(func.round(func.avg(Employee.salary), 2), 0),
            func.coalesce(median_numeric, 0),
        ).where(*conditions)
        headcount, total_annual, average, median = (
            await self._session.execute(stmt)
        ).one()
        return CostAggregate(
            headcount=headcount,
            total_annual=Decimal(total_annual),
            average=Decimal(average),
            median=Decimal(median),
        )
