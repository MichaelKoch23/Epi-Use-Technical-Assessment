"""§ import: schema validation, duplicate numbers, unknown managers, cycles
introduced by the file itself (checked against the WHOLE graph, not row by
row), future birth dates, negative salaries, and the all-or-nothing commit
— a partial import is worse than none.
"""

from __future__ import annotations

import io

import openpyxl
from fastapi import UploadFile

from app.adapters.spreadsheet import parse_csv, parse_xlsx
from app.core.security import Principal
from app.repositories.employee_repository import EmployeeRepository
from app.routers.imports import import_employees
from app.services.import_service import ImportService


def _row(number, *, manager="", **overrides):
    row = {
        "employee_number": number,
        "first_name": "First",
        "last_name": number,
        "email": f"{number.lower()}@example.com",
        "birth_date": "1990-01-01",
        "position": "Engineer",
        "salary": "50000",
        "currency": "ZAR",
        "manager_employee_number": manager,
    }
    row.update(overrides)
    return row


def _outcomes(plan):
    return {r.employee_number: (r.outcome, r.reason) for r in plan.rows}


async def test_new_and_existing_rows_classified_create_and_update(
    db_session, employee_factory
):
    existing = await employee_factory(employee_number="E-100")
    rows = [_row("E-100"), _row("E-200")]

    plan = await ImportService(db_session).validate(rows)

    outcomes = _outcomes(plan)
    assert outcomes["E-100"][0] == "will_update"
    assert outcomes["E-200"][0] == "will_create"
    assert plan.blocked_count == 0
    assert existing.employee_number == "E-100"  # fixture created it, unused otherwise


async def test_missing_required_field_blocks_row(db_session):
    rows = [_row("E-100", last_name="")]
    plan = await ImportService(db_session).validate(rows)

    row = plan.rows[0]
    assert row.outcome == "blocked"
    assert "last_name" in row.reason


async def test_invalid_birth_date_format_blocks_row(db_session):
    rows = [_row("E-100", birth_date="not-a-date")]
    plan = await ImportService(db_session).validate(rows)
    assert plan.rows[0].outcome == "blocked"
    assert "birth_date" in plan.rows[0].reason


async def test_duplicate_employee_number_in_file_blocks_all_copies(db_session):
    rows = [_row("E-100"), _row("E-100")]
    plan = await ImportService(db_session).validate(rows)

    assert all(r.outcome == "blocked" for r in plan.rows)
    assert all("appears more than once" in r.reason for r in plan.rows)


async def test_future_birth_date_blocked(db_session):
    rows = [_row("E-100", birth_date="2999-01-01")]
    plan = await ImportService(db_session).validate(rows)
    assert plan.rows[0].outcome == "blocked"
    assert "future" in plan.rows[0].reason


async def test_negative_salary_blocked(db_session):
    rows = [_row("E-100", salary="-1")]
    plan = await ImportService(db_session).validate(rows)
    assert plan.rows[0].outcome == "blocked"
    assert "negative" in plan.rows[0].reason


async def test_unknown_manager_blocked(db_session):
    rows = [_row("E-100", manager="NOPE")]
    plan = await ImportService(db_session).validate(rows)
    assert plan.rows[0].outcome == "blocked"
    assert "not found" in plan.rows[0].reason


async def test_self_reference_manager_blocked_as_cycle(db_session):
    rows = [_row("E-100", manager="E-100")]
    plan = await ImportService(db_session).validate(rows)
    assert plan.rows[0].outcome == "blocked"
    assert "cycle" in plan.rows[0].reason


async def test_two_row_cycle_introduced_purely_by_the_file_blocked(db_session):
    rows = [_row("E-100", manager="E-200"), _row("E-200", manager="E-100")]
    plan = await ImportService(db_session).validate(rows)

    assert all(r.outcome == "blocked" for r in plan.rows)
    assert all("cycle" in r.reason for r in plan.rows)


async def test_cycle_spanning_existing_db_rows_and_a_file_edit_blocked(
    db_session, employee_factory
):
    root = await employee_factory(employee_number="E-ROOT")
    child = await employee_factory(employee_number="E-CHILD", manager_id=root.id)

    # The file tries to reparent the root under its own existing descendant
    # — a cycle that only exists once the file's proposed edge is combined
    # with the DB's own existing graph, not visible from either alone.
    rows = [_row("E-ROOT", manager="E-CHILD")]
    plan = await ImportService(db_session).validate(rows)

    assert plan.rows[0].outcome == "blocked"
    assert "cycle" in plan.rows[0].reason
    assert child.manager_id == root.id  # untouched, still just data setup


async def test_multiple_disjoint_cycles_each_fully_blocked(db_session):
    rows = [
        _row("A1", manager="A2"),
        _row("A2", manager="A1"),
        _row("B1", manager="B2"),
        _row("B2", manager="B1"),
        _row("C1"),  # unrelated, valid row in the same file
    ]
    plan = await ImportService(db_session).validate(rows)
    outcomes = _outcomes(plan)

    assert outcomes["A1"][0] == "blocked"
    assert outcomes["A2"][0] == "blocked"
    assert outcomes["B1"][0] == "blocked"
    assert outcomes["B2"][0] == "blocked"
    assert outcomes["C1"][0] == "will_create"


async def test_unresolvable_manager_row_does_not_poison_other_valid_references(
    db_session,
):
    """A row blocked for an unrelated reason (bad salary) but with a
    resolvable identity must still count as a valid graph node — otherwise
    a second, perfectly fine row that legitimately reports to it would be
    incorrectly flagged 'unknown manager' too."""
    rows = [_row("E-BOSS", salary="-1"), _row("E-REPORT", manager="E-BOSS")]
    plan = await ImportService(db_session).validate(rows)
    outcomes = _outcomes(plan)

    assert outcomes["E-BOSS"][0] == "blocked"
    assert "negative" in outcomes["E-BOSS"][1]
    assert outcomes["E-REPORT"][0] == "will_create"
    assert outcomes["E-REPORT"][1] is None


async def test_commit_writes_nothing_when_any_row_is_blocked(
    db_session, actor_id, employee_factory
):
    rows = [_row("E-GOOD"), _row("E-BAD", last_name="")]
    service = ImportService(db_session)
    plan = await service.validate(rows)

    result = await service.commit(plan, actor_id=actor_id)
    assert result.committed is False

    repo = EmployeeRepository(db_session)
    assert await repo.get_by_employee_number("E-GOOD") is None


async def test_commit_applies_whole_file_in_one_transaction(
    db_session, actor_id, employee_factory
):
    rows = [_row("E-BOSS"), _row("E-REPORT", manager="E-BOSS")]
    service = ImportService(db_session)
    plan = await service.validate(rows)

    result = await service.commit(plan, actor_id=actor_id)
    await db_session.commit()

    assert result.committed is True
    assert result.created == 2

    repo = EmployeeRepository(db_session)
    boss = await repo.get_by_employee_number("E-BOSS")
    report = await repo.get_by_employee_number("E-REPORT")
    assert boss is not None and report is not None
    assert report.manager_id == boss.id


async def test_dry_run_via_router_never_writes(db_session, actor_id):
    csv_bytes = (
        b"employee_number,first_name,last_name,email,birth_date,position,"
        b"salary,currency,manager_employee_number\n"
        b"E-1,Ada,Lovelace,ada@example.com,1990-01-01,Engineer,50000,ZAR,\n"
    )
    upload = UploadFile(file=io.BytesIO(csv_bytes), filename="employees.csv")
    principal = Principal(id=actor_id, role="hr_admin")

    result = await import_employees(
        file=upload, dry_run=True, session=db_session, principal=principal
    )

    assert result.committed is False
    assert result.created == 1
    repo = EmployeeRepository(db_session)
    assert await repo.get_by_employee_number("E-1") is None


async def test_commit_via_router_actually_writes(db_session, actor_id):
    csv_bytes = (
        b"employee_number,first_name,last_name,email,birth_date,position,"
        b"salary,currency,manager_employee_number\n"
        b"E-2,Grace,Hopper,grace@example.com,1990-01-01,Engineer,50000,ZAR,\n"
    )
    upload = UploadFile(file=io.BytesIO(csv_bytes), filename="employees.csv")
    principal = Principal(id=actor_id, role="hr_admin")

    result = await import_employees(
        file=upload, dry_run=False, session=db_session, principal=principal
    )

    assert result.committed is True
    repo = EmployeeRepository(db_session)
    assert await repo.get_by_employee_number("E-2") is not None


def test_parse_csv_strips_bom_and_whitespace():
    content = "employee_number,first_name\nE-1, Ada \n".encode("utf-8-sig")
    rows = parse_csv(content)
    assert rows == [{"employee_number": "E-1", "first_name": "Ada"}]


def test_parse_xlsx_reads_first_sheet():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["employee_number", "first_name"])
    sheet.append(["E-1", "Ada"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    rows = parse_xlsx(buffer.getvalue())
    assert rows == [{"employee_number": "E-1", "first_name": "Ada"}]
