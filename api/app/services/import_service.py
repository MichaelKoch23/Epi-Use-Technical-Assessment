"""Bulk CSV/XLSX import — validate the whole file (including the reporting
graph it would produce) before writing anything, then apply it as one
all-or-nothing transaction (§ import). `validate()` is pure; `commit()`
only ever writes when nothing in the plan is blocked, so a partial import
never happens."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.repositories.employee_repository import MAX_REPORTING_DEPTH, EmployeeRepository
from app.schemas.import_ import ImportResult, ImportRowOutcome, ImportRowResult
from app.services.employee_service import EmployeeService
from app.services.reassignment_service import ReassignmentService

_REQUIRED_TEXT_FIELDS = ("first_name", "last_name", "email", "position")


@dataclass
class _Row:
    row_number: int
    employee_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    birth_date: date | None = None
    position: str | None = None
    salary: Decimal | None = None
    currency: str = "ZAR"
    manager_employee_number: str | None = None
    manager_known: bool = True
    reason: str | None = None
    outcome: ImportRowOutcome = "blocked"

    def block(self, reason: str) -> None:
        if self.reason is None:
            self.reason = reason

    @property
    def display_name(self) -> str | None:
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or None


@dataclass
class ImportPlan:
    rows: list[_Row] = field(default_factory=list)

    @property
    def blocked_count(self) -> int:
        return sum(1 for r in self.rows if r.outcome == "blocked")

    def to_result(self, *, committed: bool) -> ImportResult:
        return ImportResult(
            rows=[
                ImportRowResult(
                    row_number=r.row_number,
                    employee_number=r.employee_number,
                    name=r.display_name,
                    outcome=r.outcome,
                    reason=r.reason,
                )
                for r in self.rows
            ],
            created=sum(1 for r in self.rows if r.outcome == "will_create"),
            updated=sum(1 for r in self.rows if r.outcome == "will_update"),
            blocked=self.blocked_count,
            committed=committed,
        )


def _parse_row(row_number: int, raw: dict[str, str]) -> _Row:
    row = _Row(row_number=row_number)

    number = (raw.get("employee_number") or "").strip()
    if not number:
        row.block("employee_number is required")
        return row
    row.employee_number = number

    row.first_name = (raw.get("first_name") or "").strip() or None
    row.last_name = (raw.get("last_name") or "").strip() or None
    row.email = (raw.get("email") or "").strip() or None
    row.position = (raw.get("position") or "").strip() or None
    row.currency = (raw.get("currency") or "ZAR").strip().upper() or "ZAR"
    manager_number = (raw.get("manager_employee_number") or "").strip()
    row.manager_employee_number = manager_number or None

    missing = [f for f in _REQUIRED_TEXT_FIELDS if not getattr(row, f)]
    birth_date_raw = (raw.get("birth_date") or "").strip()
    salary_raw = (raw.get("salary") or "").strip()
    if not birth_date_raw:
        missing.append("birth_date")
    if not salary_raw:
        missing.append("salary")
    if missing:
        row.block(f"missing required field(s): {', '.join(missing)}")
        return row

    try:
        row.birth_date = date.fromisoformat(birth_date_raw)
    except ValueError:
        row.block(f"invalid birth_date {birth_date_raw!r} (expected YYYY-MM-DD)")
        return row

    try:
        row.salary = Decimal(salary_raw)
    except InvalidOperation:
        row.block(f"invalid salary {salary_raw!r}")
        return row

    if row.email is not None and "@" not in row.email:
        row.block(f"invalid email {row.email!r}")
        return row

    return row


def _check_duplicate_numbers(rows: list[_Row]) -> None:
    groups: dict[str, list[_Row]] = {}
    for row in rows:
        if row.employee_number is not None:
            groups.setdefault(row.employee_number, []).append(row)
    for number, group in groups.items():
        if len(group) > 1:
            for row in group:
                row.block(f"employee_number {number!r} appears more than once in the file")


def _check_business_rules(rows: list[_Row], today: date) -> None:
    for row in rows:
        if row.birth_date is not None and row.birth_date > today:
            row.block(f"birth_date {row.birth_date.isoformat()} is in the future")
        if row.salary is not None and row.salary < 0:
            row.block(f"salary {row.salary} is negative")


def _find_cycle_members(graph: dict[str, str | None]) -> set[str]:
    """Every functional graph (≤1 outgoing edge per node — `manager_id` is
    singular, same shape the DB's own `employee_no_cycle` trigger and
    `EmployeeRepository.get_ancestors`/`is_descendant` walk) can be checked
    for cycles with a single pass per node: walk its manager chain, and if
    the walk revisits a node still on its own current path, everything from
    that node onward is a cycle. Completed, cycle-free nodes are memoized
    so no node is walked twice."""
    resolved: set[str] = set()
    cycle_members: set[str] = set()

    for start in graph:
        if start in resolved:
            continue
        path: list[str] = []
        index_in_path: dict[str, int] = {}
        node: str | None = start
        hops = 0
        while node is not None and node not in resolved and hops <= MAX_REPORTING_DEPTH:
            if node in index_in_path:
                cycle_members.update(path[index_in_path[node] :])
                break
            index_in_path[node] = len(path)
            path.append(node)
            node = graph.get(node)
            hops += 1
        resolved.update(path)

    return cycle_members


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)

    async def validate(self, raw_rows: list[dict[str, str]]) -> ImportPlan:
        # Row 1 is the header, so the first data row is row 2 — matching
        # what a user editing the file in a spreadsheet program sees.
        rows = [_parse_row(i + 2, raw) for i, raw in enumerate(raw_rows)]

        _check_duplicate_numbers(rows)
        _check_business_rules(rows, today=self._today())

        identity_map = await self._repo.list_active_identity_map()
        existing_by_number = {number: emp_id for emp_id, number, _ in identity_map}
        number_by_id = {emp_id: number for emp_id, number, _ in identity_map}
        db_graph: dict[str, str | None] = {
            number: (number_by_id.get(manager_id) if manager_id is not None else None)
            for _, number, manager_id in identity_map
        }

        file_numbers = {r.employee_number for r in rows if r.employee_number is not None}
        for row in rows:
            if row.employee_number is None or row.manager_employee_number is None:
                continue
            row.manager_known = (
                row.manager_employee_number in file_numbers
                or row.manager_employee_number in existing_by_number
            )
            if not row.manager_known:
                row.block(
                    f"manager {row.manager_employee_number!r} not found in the "
                    "file or the database"
                )

        combined_graph = dict(db_graph)
        for row in rows:
            if row.employee_number is None:
                continue
            combined_graph[row.employee_number] = (
                row.manager_employee_number if row.manager_known else None
            )

        cycle_members = _find_cycle_members(combined_graph)
        for row in rows:
            if row.employee_number in cycle_members:
                row.block("this change would create a reporting cycle")

        for row in rows:
            if row.reason is not None:
                row.outcome = "blocked"
            elif row.employee_number in existing_by_number:
                row.outcome = "will_update"
            else:
                row.outcome = "will_create"

        return ImportPlan(rows=rows)

    async def commit(self, plan: ImportPlan, *, actor_id: uuid.UUID) -> ImportResult:
        if plan.blocked_count > 0:
            return plan.to_result(committed=False)

        employee_service = EmployeeService(self._session)
        reassignment_service = ReassignmentService(self._session)

        by_number: dict[str, Employee] = {}
        for row in plan.rows:
            assert row.employee_number is not None  # nothing blocked (checked above)
            if row.outcome == "will_create":
                employee = await employee_service.create(
                    employee_number=row.employee_number,
                    first_name=row.first_name or "",
                    last_name=row.last_name or "",
                    email=row.email or "",
                    birth_date=row.birth_date or self._today(),
                    position=row.position or "",
                    salary=row.salary or Decimal(0),
                    currency=row.currency,
                    manager_id=None,
                    actor_id=actor_id,
                )
            else:
                existing = await self._repo.get_by_employee_number(row.employee_number)
                assert existing is not None
                # A non-blocked row's required fields were already confirmed
                # present by `_parse_row` — these asserts are for mypy, not
                # a runtime possibility.
                assert row.first_name is not None
                assert row.last_name is not None
                assert row.email is not None
                assert row.birth_date is not None
                assert row.position is not None
                assert row.salary is not None
                employee = await employee_service.update(
                    existing.id,
                    expected_version=existing.version,
                    actor_id=actor_id,
                    employee_number=row.employee_number,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    email=row.email,
                    birth_date=row.birth_date,
                    position=row.position,
                    salary=row.salary,
                    currency=row.currency,
                )
            by_number[row.employee_number] = employee

        for row in plan.rows:
            if row.employee_number is None or row.manager_employee_number is None:
                continue
            employee = by_number[row.employee_number]
            manager = by_number.get(row.manager_employee_number)
            if manager is not None:
                manager_id = manager.id
            else:
                manager_row = await self._repo.get_by_employee_number(
                    row.manager_employee_number
                )
                assert manager_row is not None
                manager_id = manager_row.id

            if employee.manager_id == manager_id:
                continue  # already correct — nothing to reassign or audit

            await reassignment_service.reassign_manager(
                employee.id,
                manager_id,
                expected_version=employee.version,
                actor_id=actor_id,
            )

        return plan.to_result(committed=True)

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()
