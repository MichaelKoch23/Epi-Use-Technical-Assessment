"""`GET /search` — the command palette's cross-entity quick search (§ FR-7).
Exercised at the router-function level, like the other tests here (see
test_hierarchy_roots.py for why)."""

from __future__ import annotations

from app.core.security import Principal
from app.routers.search import search
from app.services.deletion_policy import PromoteToRoot


async def test_search_matches_on_name(db_session, actor_id, employee_factory):
    match = await employee_factory(first_name="Zanele", last_name="Khumalo")
    await employee_factory(first_name="Someone", last_name="Else")

    principal = Principal(id=actor_id, role="viewer")
    results = await search(q="Zanele", session=db_session, principal=principal)

    assert [r.id for r in results] == [match.id]
    assert (results[0].first_name, results[0].last_name) == ("Zanele", "Khumalo")


async def test_search_matches_on_employee_number(
    db_session, actor_id, employee_factory
):
    match = await employee_factory(employee_number="EMP-99999")

    principal = Principal(id=actor_id, role="viewer")
    results = await search(q="99999", session=db_session, principal=principal)

    assert [r.id for r in results] == [match.id]


async def test_search_matches_on_position(db_session, actor_id, employee_factory):
    match = await employee_factory(position="Integration Architect")
    await employee_factory(position="Data Engineer")

    principal = Principal(id=actor_id, role="viewer")
    results = await search(q="architect", session=db_session, principal=principal)

    assert [r.id for r in results] == [match.id]


async def test_search_excludes_soft_deleted_employees(
    db_session, actor_id, employee_factory
):
    employee = await employee_factory(first_name="Ephemeral", last_name="Person")
    await PromoteToRoot(db_session).apply(employee.id, actor_id=actor_id)
    await db_session.commit()

    principal = Principal(id=actor_id, role="viewer")
    results = await search(q="Ephemeral", session=db_session, principal=principal)

    assert results == []
