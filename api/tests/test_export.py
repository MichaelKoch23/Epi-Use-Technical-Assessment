"""§ export: `GET /exports/employees.csv` honours the same filters as the
list endpoint, and - like every other employee-shaped response - never
puts a salary value in front of a viewer."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.core.pagination import EmployeeSortParams
from app.core.security import Principal
from app.repositories.employee_repository import EmployeeListFilters
from app.routers.exports import export_employees_csv

_DEFAULT_FILTERS = EmployeeListFilters()
_DEFAULT_SORT = EmployeeSortParams(sort="last_name", order="asc")


async def _csv_text(response) -> str:
    return "".join([chunk async for chunk in response.body_iterator])


async def test_viewer_export_has_no_salary_column(
    db_session, actor_id, employee_factory
):
    await employee_factory(salary=Decimal(123456))
    viewer = Principal(id=uuid.uuid4(), role="viewer")

    response = await export_employees_csv(
        filters=_DEFAULT_FILTERS,
        sort_params=_DEFAULT_SORT,
        session=db_session,
        principal=viewer,
    )
    text = await _csv_text(response)

    header = text.splitlines()[0]
    assert "salary" not in header.split(",")
    assert "123456" not in text


async def test_admin_export_includes_salary_column_and_value(
    db_session, actor_id, employee_factory
):
    await employee_factory(salary=Decimal(123456))
    admin = Principal(id=actor_id, role="hr_admin")

    response = await export_employees_csv(
        filters=_DEFAULT_FILTERS,
        sort_params=_DEFAULT_SORT,
        session=db_session,
        principal=admin,
    )
    text = await _csv_text(response)

    header = text.splitlines()[0]
    assert "salary" in header.split(",")
    assert "123456" in text


async def test_export_honours_current_filters(db_session, actor_id, employee_factory):
    await employee_factory(position="Engineer")
    await employee_factory(position="Manager")
    admin = Principal(id=actor_id, role="hr_admin")

    filters = EmployeeListFilters(position="Engineer")
    response = await export_employees_csv(
        filters=filters,
        sort_params=_DEFAULT_SORT,
        session=db_session,
        principal=admin,
    )
    text = await _csv_text(response)

    data_lines = [line for line in text.splitlines()[1:] if line]
    assert len(data_lines) == 1
    assert "Engineer" in data_lines[0]


async def test_export_resolves_manager_employee_number(
    db_session, actor_id, employee_factory
):
    manager = await employee_factory(employee_number="E-MGR")
    await employee_factory(employee_number="E-REP", manager_id=manager.id)
    admin = Principal(id=actor_id, role="hr_admin")

    response = await export_employees_csv(
        filters=_DEFAULT_FILTERS,
        sort_params=_DEFAULT_SORT,
        session=db_session,
        principal=admin,
    )
    text = await _csv_text(response)

    report_line = next(line for line in text.splitlines() if "E-REP" in line)
    assert "E-MGR" in report_line


async def test_export_neutralises_spreadsheet_formulas(
    db_session, actor_id, employee_factory
):
    """CSV injection (CWE-1236): a field beginning `=`, `+`, `-` or `@` is
    executed as a formula when the download is opened in Excel or
    LibreOffice, so an employee record is enough to attack whoever exports
    it. The value must survive intact, prefixed so it is read as text."""
    payload = "=cmd|'/c calc'!A1"
    await employee_factory(first_name=payload, position="@SUM(1+1)")
    admin = Principal(id=actor_id, role="hr_admin")

    response = await export_employees_csv(
        filters=_DEFAULT_FILTERS,
        sort_params=_DEFAULT_SORT,
        session=db_session,
        principal=admin,
    )
    text = await _csv_text(response)

    assert f"'{payload}" in text
    assert "'@SUM(1+1)" in text
    # No cell is left starting with a bare formula character.
    for line in text.splitlines()[1:]:
        for cell in line.split(","):
            assert not cell.startswith(("=", "+", "@")), cell


async def test_viewer_cannot_use_salary_filters_on_the_export(
    db_session, actor_id, employee_factory
):
    """The column being absent does not stop bisection - see
    `require_salary_access`."""
    import pytest
    from fastapi import HTTPException

    await employee_factory(salary=Decimal(900000))
    viewer = Principal(id=uuid.uuid4(), role="viewer")

    with pytest.raises(HTTPException) as exc_info:
        await export_employees_csv(
            filters=EmployeeListFilters(min_salary=Decimal(500000)),
            sort_params=_DEFAULT_SORT,
            session=db_session,
            principal=viewer,
        )
    assert exc_info.value.status_code == 403
