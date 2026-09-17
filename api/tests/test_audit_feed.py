"""`GET /audit` - the global change-history feed behind the topbar's
"Change history" button (§ global audit feed), spanning every employee
rather than one. Exercised at the router-function level, like the other
tests here (see test_hierarchy_roots.py for why)."""

from __future__ import annotations

import json

from app.core.pagination import PageParams
from app.core.security import Principal
from app.routers.audit import list_audit_log
from app.services.employee_service import EmployeeService

_PAGE = PageParams(page=1, page_size=50)


async def test_feed_spans_every_employee(db_session, actor_id, employee_factory):
    a = await employee_factory(first_name="Aaron", last_name="First")
    b = await employee_factory(first_name="Beatrice", last_name="Second")

    principal = Principal(id=actor_id, role="hr_admin")
    page = await list_audit_log(
        pagination=_PAGE, session=db_session, principal=principal
    )

    employee_ids = {item.employee_id for item in page.items}
    assert {a.id, b.id} <= employee_ids


async def test_feed_newest_first(db_session, actor_id, employee_factory):
    await employee_factory()
    second = await employee_factory()

    principal = Principal(id=actor_id, role="hr_admin")
    page = await list_audit_log(
        pagination=_PAGE, session=db_session, principal=principal
    )

    assert page.items[0].employee_id == second.id


async def test_feed_carries_employee_name(db_session, actor_id, employee_factory):
    employee = await employee_factory(first_name="Naledi", last_name="Dube")

    principal = Principal(id=actor_id, role="hr_admin")
    page = await list_audit_log(
        pagination=_PAGE, session=db_session, principal=principal
    )

    entry = next(item for item in page.items if item.employee_id == employee.id)
    assert entry.employee_name == "Naledi Dube"


async def test_viewer_response_has_no_salary_in_snapshots(
    db_session, actor_id, employee_factory
):
    await employee_factory(salary=123456)

    viewer = Principal(id=actor_id, role="viewer")
    page = await list_audit_log(pagination=_PAGE, session=db_session, principal=viewer)

    body = json.loads(page.model_dump_json())
    for item in body["items"]:
        if item["after"] is not None:
            assert "salary" not in item["after"]


async def test_feed_still_shows_deleted_employees_by_name(
    db_session, actor_id, employee_factory
):
    employee = await employee_factory(first_name="Gone", last_name="Soon")
    await EmployeeService(db_session).soft_delete(employee.id, actor_id=actor_id)
    await db_session.commit()

    principal = Principal(id=actor_id, role="hr_admin")
    page = await list_audit_log(
        pagination=_PAGE, session=db_session, principal=principal
    )

    entry = next(item for item in page.items if item.employee_id == employee.id)
    assert entry.employee_name == "Gone Soon"
