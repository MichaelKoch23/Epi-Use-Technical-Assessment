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
    id: uuid.UUID
    name: str
    position: str
    depth: int


@dataclass(frozen=True, slots=True)
class SpanRow:
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
        conditions = [Employee.deleted_at.is_(None)]
        if ids is not None:
            conditions.append(Employee.id.in_(ids))

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
