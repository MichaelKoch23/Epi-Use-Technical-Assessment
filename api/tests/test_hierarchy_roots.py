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
