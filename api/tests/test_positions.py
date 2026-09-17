"""`GET /employees/positions` - distinct positions for the list page's
position filter dropdown. Exercised at the router-function level, like the
other tests here (see test_hierarchy_roots.py for why)."""

from __future__ import annotations

from app.core.security import Principal
from app.routers.employees import list_positions
from app.services.deletion_policy import PromoteToRoot


async def test_positions_are_distinct_and_sorted(
    db_session, actor_id, employee_factory
):
    await employee_factory(position="Data Engineer")
    await employee_factory(position="Architect")
    await employee_factory(position="Data Engineer")

    principal = Principal(id=actor_id, role="viewer")
    positions = await list_positions(session=db_session, _principal=principal)

    assert positions == ["Architect", "Data Engineer"]


async def test_positions_exclude_soft_deleted_employees(
    db_session, actor_id, employee_factory
):
    await employee_factory(position="Data Engineer")
    gone = await employee_factory(position="Ephemeral Role")
    await PromoteToRoot(db_session).apply(gone.id, actor_id=actor_id)
    await db_session.commit()

    principal = Principal(id=actor_id, role="viewer")
    positions = await list_positions(session=db_session, _principal=principal)

    assert positions == ["Data Engineer"]
