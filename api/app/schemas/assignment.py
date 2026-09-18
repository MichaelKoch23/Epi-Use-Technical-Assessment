from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.employee import EmployeeHierarchyNode, EmployeeReadAny


class AsOfEmployees(BaseModel):
    as_of: date
    items: list[EmployeeReadAny]


class AsOfHierarchy(BaseModel):
    as_of: date
    items: list[EmployeeHierarchyNode]


class PersonRefRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str


class CancelledAssignmentRead(BaseModel):
    id: uuid.UUID
    manager_id: uuid.UUID | None
    manager_name: str | None
    effective_from: date
    reason: str | None


class ManagerReassignRead(BaseModel):
    """The outcome of a reassignment, which may not have taken effect yet."""

    employee: EmployeeReadAny
    assignment_id: uuid.UUID
    effective_from: date
    in_force_now: bool
    reason: str | None
    cancelled: list[CancelledAssignmentRead]


class MovePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_manager_id: uuid.UUID | None = None
    as_of: date | None = None


class MoveAffectedRead(BaseModel):
    id: uuid.UUID
    name: str
    position: str
    depth: int


class CostDeltaRead(BaseModel):
    leaving: Decimal
    arriving: Decimal
    currency: str


class _MovePreviewBase(BaseModel):
    as_of: date
    employee: PersonRefRead
    affected: list[MoveAffectedRead]
    headcount: int
    current_manager: PersonRefRead | None
    new_manager: PersonRefRead | None
    depth_change: int
    blocked: bool
    blocked_chain: list[uuid.UUID] = Field(default_factory=list)
    blocked_chain_names: list[str] = Field(default_factory=list)
    blocked_at: date | None = None
    supersedes: list[CancelledAssignmentRead]


class MovePreviewRead(_MovePreviewBase):
    cost_delta: CostDeltaRead


class MovePreviewReadRestricted(_MovePreviewBase):
    pass


MovePreviewReadAny = MovePreviewRead | MovePreviewReadRestricted


class AssignmentHistoryItemRead(BaseModel):
    id: uuid.UUID
    manager_id: uuid.UUID | None
    manager_name: str | None
    valid_from: date
    valid_to: date | None
    reason: str | None
    created_by_email: str | None
    created_at: datetime
    in_force: bool
    scheduled: bool


class AssignmentHistoryRead(BaseModel):
    employee_id: uuid.UUID
    as_of: date
    items: list[AssignmentHistoryItemRead]


class ScheduledAssignmentRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    employee_position: str
    manager_id: uuid.UUID | None
    manager_name: str | None
    effective_from: date
    reason: str | None
    created_by_email: str | None
    created_at: datetime


class ScheduledAssignmentsRead(BaseModel):
    as_of: date
    items: list[ScheduledAssignmentRead]


class ManagerChangeRead(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    from_manager_id: uuid.UUID | None
    from_manager_name: str | None
    to_manager_id: uuid.UUID | None
    to_manager_name: str | None
    subtree_size: int


class DiffCostRead(BaseModel):
    total_moved: Decimal
    currency: str


class _StructureDiffBase(BaseModel):
    from_date: date
    to_date: date
    manager_changes: list[ManagerChangeRead]
    branch_moves: list[ManagerChangeRead]
    became_root: list[ManagerChangeRead]
    stopped_being_root: list[ManagerChangeRead]
    max_depth_from: int
    max_depth_to: int
    max_depth_change: int
    average_span_from: float
    average_span_to: float
    average_span_change: float


class StructureDiffRead(_StructureDiffBase):
    cost: DiffCostRead


class StructureDiffReadRestricted(_StructureDiffBase):
    pass


StructureDiffReadAny = StructureDiffRead | StructureDiffReadRestricted
