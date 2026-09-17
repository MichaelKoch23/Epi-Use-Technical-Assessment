from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel


class DepthCountRead(BaseModel):
    depth: int
    count: int


class SpanCountRead(BaseModel):
    direct_reports: int
    manager_count: int


class WideSpanAnomalyRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str
    direct_reports: int


class SingleReportAnomalyRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str
    direct_reports: int


class DeepChainAnomalyRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str
    depth: int


class UnreachableAnomalyRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str


class AnomaliesRead(BaseModel):
    wide_spans: list[WideSpanAnomalyRead]
    single_report_managers: list[SingleReportAnomalyRead]
    deep_chains: list[DeepChainAnomalyRead]
    unreachable: list[UnreachableAnomalyRead]


class CostSummaryRead(BaseModel):
    total_annual: Decimal
    average: Decimal
    median: Decimal
    currency: str = "ZAR"


class _OrgSummaryBase(BaseModel):
    headcount: int
    root_count: int
    manager_count: int
    individual_contributor_count: int
    max_depth: int
    average_span_of_control: float
    median_span_of_control: float
    depth_distribution: list[DepthCountRead]
    span_distribution: list[SpanCountRead]
    anomalies: AnomaliesRead


class OrgSummaryRead(_OrgSummaryBase):
    cost: CostSummaryRead


class OrgSummaryReadRestricted(_OrgSummaryBase):
    pass


OrgSummaryReadAny = OrgSummaryRead | OrgSummaryReadRestricted


class BranchEmployeeRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str


class _BranchSummaryBase(BaseModel):
    employee: BranchEmployeeRead
    headcount: int
    direct_reports: int
    depth_below: int
    average_span_of_control: float


class BranchSummaryRead(_BranchSummaryBase):
    cost: CostSummaryRead


class BranchSummaryReadRestricted(_BranchSummaryBase):
    pass


BranchSummaryReadAny = BranchSummaryRead | BranchSummaryReadRestricted
