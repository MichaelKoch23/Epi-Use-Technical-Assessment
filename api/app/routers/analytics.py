"""`/api/v1/analytics/*` — the org-structure dashboard (§ analytics). Both
routes are viewer-accessible; the `cost` object is field-level gated
(§9.3) rather than the endpoint being admin-only, the same pattern
`to_employee_read` already applies everywhere else."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.repositories.analytics_repository import CostAggregate
from app.schemas.analytics import (
    AnomaliesRead,
    BranchEmployeeRead,
    BranchSummaryRead,
    BranchSummaryReadAny,
    BranchSummaryReadRestricted,
    CostSummaryRead,
    DeepChainAnomalyRead,
    DepthCountRead,
    OrgSummaryRead,
    OrgSummaryReadAny,
    OrgSummaryReadRestricted,
    SingleReportAnomalyRead,
    SpanCountRead,
    UnreachableAnomalyRead,
    WideSpanAnomalyRead,
)
from app.services.analytics_service import (
    AnalyticsService,
    BranchSummaryData,
    OrgSummaryData,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _to_anomalies_read(anomalies: OrgSummaryData) -> AnomaliesRead:
    a = anomalies.anomalies
    return AnomaliesRead(
        wide_spans=[
            WideSpanAnomalyRead(
                id=row.id,
                name=row.name,
                position=row.position,
                direct_reports=row.direct_reports,
            )
            for row in a.wide_spans
        ],
        single_report_managers=[
            SingleReportAnomalyRead(
                id=row.id,
                name=row.name,
                position=row.position,
                direct_reports=row.direct_reports,
            )
            for row in a.single_report_managers
        ],
        deep_chains=[
            DeepChainAnomalyRead(
                id=row.id, name=row.name, position=row.position, depth=row.depth
            )
            for row in a.deep_chains
        ],
        unreachable=[
            UnreachableAnomalyRead(id=row.id, name=row.name, position=row.position)
            for row in a.unreachable
        ],
    )


def _cost_summary_read(cost: CostAggregate) -> CostSummaryRead:
    return CostSummaryRead(
        total_annual=cost.total_annual, average=cost.average, median=cost.median
    )


def to_org_summary_read(
    data: OrgSummaryData, principal: Principal
) -> OrgSummaryReadAny:
    depth_distribution = [
        DepthCountRead(depth=d.depth, count=d.count) for d in data.depth_distribution
    ]
    span_distribution = [
        SpanCountRead(direct_reports=s.direct_reports, manager_count=s.count)
        for s in data.span_distribution
    ]
    anomalies = _to_anomalies_read(data)

    if principal.is_admin:
        assert data.cost is not None  # the service never omits it for an admin
        return OrgSummaryRead(
            headcount=data.headcount,
            root_count=data.root_count,
            manager_count=data.manager_count,
            individual_contributor_count=data.individual_contributor_count,
            max_depth=data.max_depth,
            average_span_of_control=data.average_span_of_control,
            median_span_of_control=data.median_span_of_control,
            depth_distribution=depth_distribution,
            span_distribution=span_distribution,
            anomalies=anomalies,
            cost=_cost_summary_read(data.cost),
        )
    return OrgSummaryReadRestricted(
        headcount=data.headcount,
        root_count=data.root_count,
        manager_count=data.manager_count,
        individual_contributor_count=data.individual_contributor_count,
        max_depth=data.max_depth,
        average_span_of_control=data.average_span_of_control,
        median_span_of_control=data.median_span_of_control,
        depth_distribution=depth_distribution,
        span_distribution=span_distribution,
        anomalies=anomalies,
    )


def to_branch_summary_read(
    data: BranchSummaryData, principal: Principal
) -> BranchSummaryReadAny:
    employee = BranchEmployeeRead(
        id=data.employee.id,
        name=f"{data.employee.first_name} {data.employee.last_name}",
        position=data.employee.position,
    )
    if principal.is_admin:
        assert data.cost is not None
        return BranchSummaryRead(
            employee=employee,
            headcount=data.headcount,
            direct_reports=data.direct_reports,
            depth_below=data.depth_below,
            average_span_of_control=data.average_span_of_control,
            cost=_cost_summary_read(data.cost),
        )
    return BranchSummaryReadRestricted(
        employee=employee,
        headcount=data.headcount,
        direct_reports=data.direct_reports,
        depth_below=data.depth_below,
        average_span_of_control=data.average_span_of_control,
    )


@router.get("/org-summary", response_model=OrgSummaryReadAny)
async def get_org_summary(
    response: Response,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> OrgSummaryReadAny:
    service = AnalyticsService(session)
    data = await service.get_org_summary(principal)
    response.headers["Cache-Control"] = "private, max-age=60"
    return to_org_summary_read(data, principal)


@router.get("/branch/{employee_id}", response_model=BranchSummaryReadAny)
async def get_branch_summary(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> BranchSummaryReadAny:
    service = AnalyticsService(session)
    data = await service.get_branch_summary(employee_id, principal)
    return to_branch_summary_read(data, principal)
