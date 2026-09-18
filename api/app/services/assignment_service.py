from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AssignmentNotFound,
    EffectiveDateBeforeFirstAssignmentError,
    EmployeeNotFound,
    ManagerUnchangedError,
    ReportingCycleError,
    ScheduledAssignmentInForceError,
    VersionConflictError,
)
from app.models.employee import Employee
from app.models.employee_assignment import EmployeeAssignment
from app.repositories.assignment_repository import (
    AssignmentHierarchyRow,
    AssignmentHistoryRow,
    AssignmentRepository,
    ScheduledAssignmentRow,
)
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService


def today() -> date:
    return datetime.now(UTC).date()


@dataclass(frozen=True, slots=True)
class CancelledAssignment:
    id: uuid.UUID
    manager_id: uuid.UUID | None
    valid_from: date
    reason: str | None


@dataclass(frozen=True, slots=True)
class ReassignResult:
    assignment: EmployeeAssignment
    cancelled: list[CancelledAssignment]
    in_force_now: bool


@dataclass(frozen=True, slots=True)
class CostDelta:
    """The subtree's annual salary, leaving one branch and arriving in another.

    The magnitudes match: a branch move neither creates nor destroys cost, it
    relocates it. Either side is zero when there is no branch on that side -
    an employee promoted to root, or one who was already a root.
    """

    leaving: Decimal
    arriving: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class MovePreview:
    as_of: date
    employee: Employee
    subtree: list[AssignmentHierarchyRow]
    headcount: int
    current_manager: Employee | None
    new_manager: Employee | None
    depth_change: int
    cost: CostDelta | None
    blocked: bool
    blocked_chain: list[uuid.UUID]
    blocked_at: date | None
    supersedes: list[CancelledAssignment]


@dataclass(frozen=True, slots=True)
class ManagerChange:
    employee_id: uuid.UUID
    employee_name: str
    from_manager_id: uuid.UUID | None
    from_manager_name: str | None
    to_manager_id: uuid.UUID | None
    to_manager_name: str | None
    subtree_size: int


@dataclass(frozen=True, slots=True)
class StructureDiff:
    from_date: date
    to_date: date
    manager_changes: list[ManagerChange]
    branch_moves: list[ManagerChange]
    became_root: list[ManagerChange]
    stopped_being_root: list[ManagerChange]
    max_depth_from: int
    max_depth_to: int
    average_span_from: float
    average_span_to: float
    moved_salary: Decimal
    currency: str


def _average_span(edges: dict[uuid.UUID, uuid.UUID | None]) -> float:
    """Mean direct reports across employees who have at least one.

    Matches the definition the analytics summary already uses, so the two
    numbers can be compared without a footnote.
    """
    counts: dict[uuid.UUID, int] = {}
    for manager_id in edges.values():
        if manager_id is not None:
            counts[manager_id] = counts.get(manager_id, 0) + 1
    if not counts:
        return 0.0
    return round(sum(counts.values()) / len(counts), 2)


class AssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._assignments = AssignmentRepository(session)
        self._employees = EmployeeRepository(session)
        self._audit = AuditService(session)

    async def sync(self) -> int:
        return await self._assignments.sync_effective()

    async def reassign(
        self,
        employee_id: uuid.UUID,
        new_manager_id: uuid.UUID | None,
        *,
        effective_from: date | None = None,
        reason: str | None = None,
        expected_version: int | None = None,
        actor_id: uuid.UUID,
    ) -> ReassignResult:
        effective_from = effective_from or today()
        await self._assignments.sync_effective()

        locked = await self._lock(employee_id, new_manager_id)
        employee = locked[employee_id]

        if expected_version is not None and employee.version != expected_version:
            raise VersionConflictError(employee_id, expected_version, employee.version)

        earliest = await self._assignments.get_earliest_valid_from(employee_id)
        if earliest is not None and effective_from < earliest:
            raise EffectiveDateBeforeFirstAssignmentError(
                employee_id, effective_from, earliest
            )

        if new_manager_id is not None:
            await self._assert_acyclic(employee_id, new_manager_id, effective_from)

        previous_manager_id = await self._effective_manager_id(
            employee_id, effective_from
        )

        if new_manager_id == previous_manager_id:
            upcoming = await self._assignments.get_starting_on_or_after(
                employee_id, effective_from
            )
            if all(row.manager_id == new_manager_id for row in upcoming):
                raise ManagerUnchangedError(employee_id, new_manager_id)

        assignment, superseded = await self._assignments.set_edge(
            employee_id,
            new_manager_id,
            effective_from=effective_from,
            reason=reason,
            created_by=actor_id,
        )
        cancelled = [_as_cancelled(row) for row in superseded]

        in_force_now = effective_from <= today()
        await self._audit.record(
            employee_id=employee_id,
            actor_id=actor_id,
            action=(
                "employee.reassigned"
                if in_force_now
                else "employee.assignment_scheduled"
            ),
            before={"manager_id": _str_or_none(previous_manager_id)},
            after={
                "manager_id": _str_or_none(new_manager_id),
                "assignment_id": str(assignment.id),
                "effective_from": effective_from.isoformat(),
                "reason": reason,
                "cancelled_assignment_ids": [str(row.id) for row in cancelled],
            },
        )

        if in_force_now:
            await self._assignments.sync_effective(force=True)
            await self._session.refresh(employee)

        return ReassignResult(
            assignment=assignment, cancelled=cancelled, in_force_now=in_force_now
        )

    async def preview_move(
        self,
        employee_id: uuid.UUID,
        new_manager_id: uuid.UUID | None,
        *,
        as_of: date | None = None,
        include_cost: bool,
    ) -> MovePreview:
        as_of = as_of or today()

        employee = await self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        new_manager: Employee | None = None
        if new_manager_id is not None:
            new_manager = await self._employees.get(new_manager_id)
            if new_manager is None:
                raise EmployeeNotFound(new_manager_id)

        subtree = list(await self._assignments.get_subtree(employee_id, as_of))
        current_manager_id = subtree[0].employee.manager_id if subtree else None
        current_manager: Employee | None = None
        if current_manager_id is not None:
            current_manager = await self._employees.get(current_manager_id)

        blocked = False
        blocked_chain: list[uuid.UUID] = []
        blocked_at: date | None = None
        if new_manager_id is not None:
            try:
                await self._assert_acyclic(employee_id, new_manager_id, as_of)
            except ReportingCycleError as exc:
                blocked = True
                blocked_chain = exc.chain
                blocked_at = exc.at

        cost: CostDelta | None = None
        if include_cost:
            subtree_cost = await self._assignments.get_subtree_cost(employee_id, as_of)
            total = Decimal(subtree_cost.total_annual)
            cost = CostDelta(
                leaving=total if current_manager_id is not None else Decimal(0),
                arriving=total if new_manager_id is not None else Decimal(0),
                currency=subtree_cost.currency,
            )

        current_depth = await self._depth_of(employee_id, as_of)
        if new_manager_id is None:
            new_depth = 0
        else:
            new_depth = await self._depth_of(new_manager_id, as_of) + 1

        supersedes = [
            _as_cancelled(row)
            for row in await self._assignments.get_starting_on_or_after(
                employee_id, as_of, for_update=False
            )
            if row.valid_from > today()
        ]

        return MovePreview(
            as_of=as_of,
            employee=employee,
            subtree=subtree,
            headcount=len(subtree),
            current_manager=current_manager,
            new_manager=new_manager,
            depth_change=new_depth - current_depth,
            cost=cost,
            blocked=blocked,
            blocked_chain=blocked_chain,
            blocked_at=blocked_at,
            supersedes=supersedes,
        )

    async def cancel_scheduled(
        self, assignment_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> EmployeeAssignment:
        await self._assignments.sync_effective()

        assignment = await self._assignments.get(assignment_id)
        if assignment is None:
            raise AssignmentNotFound(assignment_id)
        if assignment.valid_from <= today():
            raise ScheduledAssignmentInForceError(assignment_id, assignment.valid_from)

        preceding = await self._assignments.get_preceding(
            assignment.employee_id, assignment.valid_from
        )
        await self._assignments.delete(assignment)
        await self._session.flush()

        if preceding is not None:
            preceding.valid_to = assignment.valid_to
            await self._session.flush()

        await self._audit.record(
            employee_id=assignment.employee_id,
            actor_id=actor_id,
            action="employee.assignment_cancelled",
            before={
                "assignment_id": str(assignment.id),
                "manager_id": _str_or_none(assignment.manager_id),
                "effective_from": assignment.valid_from.isoformat(),
                "reason": assignment.reason,
            },
            after=None,
        )
        return assignment

    async def diff_structure(self, from_date: date, to_date: date) -> StructureDiff:
        """Compare two dates using employee_assignment alone.

        Every edge change is already a row in that table, so no separate change
        capture is needed to answer what moved between two dates.
        """
        edges_from = await self._assignments.get_edges_at(from_date)
        edges_to = await self._assignments.get_edges_at(to_date)

        shared = edges_from.keys() & edges_to.keys()
        changed = [
            employee_id
            for employee_id in shared
            if edges_from[employee_id] != edges_to[employee_id]
        ]

        report_counts: dict[uuid.UUID, int] = {}
        for manager_id in edges_to.values():
            if manager_id is not None:
                report_counts[manager_id] = report_counts.get(manager_id, 0) + 1

        name_ids = set(changed)
        for employee_id in changed:
            for side in (edges_from[employee_id], edges_to[employee_id]):
                if side is not None:
                    name_ids.add(side)
        names = await self._employees.get_names_by_ids(list(name_ids))

        manager_changes = [
            ManagerChange(
                employee_id=employee_id,
                employee_name=names.get(employee_id, "Unknown employee"),
                from_manager_id=edges_from[employee_id],
                from_manager_name=_name_of(edges_from[employee_id], names),
                to_manager_id=edges_to[employee_id],
                to_manager_name=_name_of(edges_to[employee_id], names),
                subtree_size=report_counts.get(employee_id, 0),
            )
            for employee_id in changed
        ]
        manager_changes.sort(key=lambda change: change.employee_name)

        trees_from = await self._assignments.get_tree(from_date)
        trees_to = await self._assignments.get_tree(to_date)
        moved_salary, currency = await self._assignments.get_salary_total(changed)

        return StructureDiff(
            from_date=from_date,
            to_date=to_date,
            manager_changes=manager_changes,
            branch_moves=[c for c in manager_changes if c.subtree_size > 0],
            became_root=[
                c
                for c in manager_changes
                if c.from_manager_id is not None and c.to_manager_id is None
            ],
            stopped_being_root=[
                c
                for c in manager_changes
                if c.from_manager_id is None and c.to_manager_id is not None
            ],
            max_depth_from=max((row.depth for row in trees_from), default=0),
            max_depth_to=max((row.depth for row in trees_to), default=0),
            average_span_from=_average_span(edges_from),
            average_span_to=_average_span(edges_to),
            moved_salary=moved_salary,
            currency=currency,
        )

    async def get_assignment_history(
        self, employee_id: uuid.UUID
    ) -> Sequence[AssignmentHistoryRow]:
        if await self._employees.get_any(employee_id) is None:
            raise EmployeeNotFound(employee_id)
        return await self._assignments.get_assignment_history(employee_id)

    async def get_scheduled(
        self, after: date | None = None
    ) -> Sequence[ScheduledAssignmentRow]:
        return await self._assignments.get_scheduled(after)

    async def _assert_acyclic(
        self, employee_id: uuid.UUID, new_manager_id: uuid.UUID, effective_from: date
    ) -> None:
        """Reject a move that is cyclic at its own date or at any later one.

        The employee CHECK constraint and the deferred trigger still guard the
        present-day edge on the employee table. Neither can see a change that has
        not taken effect yet, so a move that is fine today but closes a loop once
        a scheduled change lands would pass both. That is what this covers: the
        set of dates on which the structure can change is finite and small, so
        every one of them is checked.
        """
        if new_manager_id == employee_id:
            raise ReportingCycleError(
                employee_id, new_manager_id, [employee_id], at=effective_from
            )

        dates = [
            effective_from,
            *await self._assignments.get_boundary_dates(after=effective_from),
        ]
        for at in dates:
            if await self._assignments.is_descendant(
                new_manager_id, of_id=employee_id, as_of=at
            ):
                chain = await self._cycle_chain(employee_id, new_manager_id, at)
                raise ReportingCycleError(employee_id, new_manager_id, chain, at=at)

    async def _cycle_chain(
        self, employee_id: uuid.UUID, new_manager_id: uuid.UUID, as_of: date
    ) -> list[uuid.UUID]:
        chain = [new_manager_id]
        for ancestor in await self._assignments.get_ancestors(new_manager_id, as_of):
            chain.append(ancestor.employee.id)
            if ancestor.employee.id == employee_id:
                break
        return chain

    async def _effective_manager_id(
        self, employee_id: uuid.UUID, as_of: date
    ) -> uuid.UUID | None:
        rows = await self._assignments.get_subtree(employee_id, as_of, max_depth=0)
        return rows[0].employee.manager_id if rows else None

    async def _depth_of(self, employee_id: uuid.UUID, as_of: date) -> int:
        return len(await self._assignments.get_ancestors(employee_id, as_of))

    async def _lock(
        self, employee_id: uuid.UUID, new_manager_id: uuid.UUID | None
    ) -> dict[uuid.UUID, Employee]:
        ids = sorted({employee_id} | ({new_manager_id} if new_manager_id else set()))
        locked: dict[uuid.UUID, Employee] = {}
        for row_id in ids:
            row = await self._employees.get_for_update(row_id)
            if row is None:
                raise EmployeeNotFound(row_id)
            locked[row_id] = row
        return locked


def _as_cancelled(row: EmployeeAssignment) -> CancelledAssignment:
    return CancelledAssignment(
        id=row.id,
        manager_id=row.manager_id,
        valid_from=row.valid_from,
        reason=row.reason,
    )


def _str_or_none(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _name_of(employee_id: uuid.UUID | None, names: dict[uuid.UUID, str]) -> str | None:
    if employee_id is None:
        return None
    return names.get(employee_id, "Unknown employee")
