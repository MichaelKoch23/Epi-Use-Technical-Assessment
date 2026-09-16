"""`GET /hierarchy/roots` powers the org chart's initial fetch (§7.3): the
forest of employees with no manager. Exercised at the router-function level,
like the other service/repository tests here - the app's own `get_db`
dependency binds to the real configured `DATABASE_URL`, not the ephemeral
testcontainer these fixtures use, so hitting the endpoint over HTTP would
talk to the wrong database entirely."""

from __future__ import annotations

import uuid

from app.core.security import Principal
from app.routers.hierarchy import get_roots


async def test_roots_returns_only_employees_without_a_manager(
    db_session, actor_id: uuid.UUID, employee_factory
):
    root = await employee_factory(manager_id=None)
    await employee_factory(manager_id=root.id)

    principal = Principal(id=actor_id, role="hr_admin")
    roots = await get_roots(session=db_session, principal=principal)

    assert {r.id for r in roots} == {root.id}


async def test_roots_excludes_soft_deleted_employees(
    db_session, actor_id: uuid.UUID, employee_factory
):
    from app.services.deletion_policy import PromoteToRoot

    root = await employee_factory(manager_id=None)
    await PromoteToRoot(db_session).apply(root.id, actor_id=actor_id)
    await db_session.commit()

    principal = Principal(id=actor_id, role="hr_admin")
    roots = await get_roots(session=db_session, principal=principal)

    assert roots == []
