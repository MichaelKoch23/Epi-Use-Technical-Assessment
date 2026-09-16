"""Orchestrates the org-structure dashboard (§ analytics): pulls the raw
rows the repository exposes, applies the thresholds from `core.constants`,
and hands the router a plain DTO. Knows nothing about HTTP or response
schemas - that translation is the router's job (§3.4), same split as every
other feature here."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from statistics import median as statistics_median

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ANOMALY_LIST_LIMIT,
    DEEP_CHAIN_THRESHOLD,
    WIDE_SPAN_THRESHOLD,
)
from app.core.exceptions import EmployeeNotFound
from app.core.security import Principal
from app.models.employee import Employee
from app.repositories.analytics_repository import (
    AnalyticsRepository,
    CostAggregate,
    DepthRow,
    SpanRow,
    UnreachableRow,
)
from app.repositories.employee_repository import EmployeeRepository


@dataclass(frozen=True, slots=True)
class DepthCount:
    depth: int
    count: int


@dataclass(frozen=True, slots=True)
class SpanCount:
    direct_reports: int
    count: int


@dataclass(frozen=True, slots=True)
class Anomalies:
    wide_spans: list[SpanRow]
    single_report_managers: list[SpanRow]
    deep_chains: list[DepthRow]
    unreachable: list[UnreachableRow]


@dataclass(frozen=True, slots=True)
class OrgSummaryData:
    headcount: int
    root_count: int
    manager_count: int
    individual_contributor_count: int
    max_depth: int
    average_span_of_control: float
    median_span_of_control: float
    depth_distribution: list[DepthCount]
    span_distribution: list[SpanCount]
    anomalies: Anomalies
    cost: CostAggregate | None


@dataclass(frozen=True, slots=True)
class BranchSummaryData:
    employee: Employee
    headcount: int
    direct_reports: int
    depth_below: int
    average_span_of_control: float
    cost: CostAggregate | None


_CACHE_TTL_SECONDS = 60
# Process-local cache keyed by role (§ analytics: "an in-process TTL cache
# is correct at this scale" - Cloud Run instances being independent is
# acceptable for a 60-second window). `clear_org_summary_cache` exists only
# so tests that mutate data between calls aren't served a stale entry.
_org_summary_cache: dict[str, tuple[float, OrgSummaryData]] = {}


def clear_org_summary_cache() -> None:
    _org_summary_cache.clear()


def _cache_key(principal: Principal) -> str:
    return "admin" if principal.is_admin else "viewer"


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AnalyticsRepository(session)
        self._employees = EmployeeRepository(session)

    async def get_org_summary(self, principal: Principal) -> OrgSummaryData:
        key = _cache_key(principal)
        cached = _org_summary_cache.get(key)
        now = time.monotonic()
        if cached is not None and cached[0] > now:
            return cached[1]

        data = await self._compute_org_summary(principal)
        _org_summary_cache[key] = (now + _CACHE_TTL_SECONDS, data)
        return data

    async def _compute_org_summary(self, principal: Principal) -> OrgSummaryData:
        depths = await self._repo.get_depths()
        spans = await self._repo.get_span_of_control()
        unreachable = await self._repo.get_unreachable(ANOMALY_LIST_LIMIT)

        depth_counts: dict[int, int] = {}
        for depth_row in depths:
            depth_counts[depth_row.depth] = depth_counts.get(depth_row.depth, 0) + 1
        depth_distribution = [
            DepthCount(depth=depth, count=count)
            for depth, count in sorted(depth_counts.items())
        ]
        max_depth = max(depth_counts, default=0)
        root_count = depth_counts.get(0, 0)

        span_counts: dict[int, int] = {}
        for span_row in spans:
            span_counts[span_row.direct_reports] = (
                span_counts.get(span_row.direct_reports, 0) + 1
            )
        span_distribution = [
            SpanCount(direct_reports=n, count=count)
            for n, count in sorted(span_counts.items())
        ]

        manager_spans = [row.direct_reports for row in spans if row.direct_reports > 0]
        manager_count = len(manager_spans)
        individual_contributor_count = len(spans) - manager_count
        average_span_of_control = (
            sum(manager_spans) / manager_count if manager_count else 0.0
        )
        median_span_of_control = (
            float(statistics_median(manager_spans)) if manager_spans else 0.0
        )

        wide_spans = sorted(
            (row for row in spans if row.direct_reports > WIDE_SPAN_THRESHOLD),
            key=lambda row: row.direct_reports,
            reverse=True,
        )[:ANOMALY_LIST_LIMIT]
        single_report_managers = [row for row in spans if row.direct_reports == 1][
            :ANOMALY_LIST_LIMIT
        ]
        deep_chains = sorted(
            (row for row in depths if row.depth >= DEEP_CHAIN_THRESHOLD),
            key=lambda row: row.depth,
            reverse=True,
        )[:ANOMALY_LIST_LIMIT]

        cost = await self._repo.get_cost_aggregate() if principal.is_admin else None

        return OrgSummaryData(
            headcount=len(spans),
            root_count=root_count,
            manager_count=manager_count,
            individual_contributor_count=individual_contributor_count,
            max_depth=max_depth,
            average_span_of_control=average_span_of_control,
            median_span_of_control=median_span_of_control,
            depth_distribution=depth_distribution,
            span_distribution=span_distribution,
            anomalies=Anomalies(
                wide_spans=wide_spans,
                single_report_managers=single_report_managers,
                deep_chains=deep_chains,
                unreachable=list(unreachable),
            ),
            cost=cost,
        )

    async def get_branch_summary(
        self, employee_id: uuid.UUID, principal: Principal
    ) -> BranchSummaryData:
        root = await self._employees.get(employee_id)
        if root is None:
            raise EmployeeNotFound(employee_id)

        rows = await self._employees.get_subtree(employee_id)
        subtree_ids = {row.employee.id for row in rows}

        direct_report_counts: dict[uuid.UUID, int] = {}
        for row in rows:
            manager_id = row.employee.manager_id
            if manager_id is not None and manager_id in subtree_ids:
                direct_report_counts[manager_id] = (
                    direct_report_counts.get(manager_id, 0) + 1
                )
        manager_spans = list(direct_report_counts.values())
        average_span_of_control = (
            sum(manager_spans) / len(manager_spans) if manager_spans else 0.0
        )

        cost = None
        if principal.is_admin:
            cost = await self._repo.get_cost_aggregate(
                [row.employee.id for row in rows]
            )

        return BranchSummaryData(
            employee=root,
            headcount=len(rows),
            direct_reports=direct_report_counts.get(employee_id, 0),
            depth_below=max((row.depth for row in rows), default=0),
            average_span_of_control=average_span_of_control,
            cost=cost,
        )
