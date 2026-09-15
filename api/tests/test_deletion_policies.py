"""§5.3: the three deletion strategies, and the preview step the UI is
required to show before a destructive delete.
"""

from __future__ import annotations

from app.repositories.employee_repository import EmployeeRepository
from app.services.deletion_policy import Cascade, PromoteToRoot, Reparent, preview


async def test_reparent_moves_reports_to_grandparent(
    db_session, actor_id, employee_factory
):
    grandparent = await employee_factory()
    parent = await employee_factory(manager_id=grandparent.id)
    child = await employee_factory(manager_id=parent.id)

    policy = Reparent(db_session)
    affected = await preview(parent.id, policy)
    assert {e.id for e in affected} == {parent.id, child.id}

    result = await policy.apply(parent.id, actor_id=actor_id)
    await db_session.commit()

    assert [e.id for e in result.deleted] == [parent.id]
    assert result.deleted[0].deleted_at is not None
    assert [e.id for e in result.reassigned] == [child.id]
    assert result.reassigned[0].manager_id == grandparent.id

    repo = EmployeeRepository(db_session)
    refreshed_child = await repo.get(child.id)
    assert refreshed_child is not None
    assert refreshed_child.manager_id == grandparent.id


async def test_reparent_on_root_degrades_to_promote_to_root(
    db_session, actor_id, employee_factory
):
    """A root has no grandparent to move reports to, so Reparent must
    fall back to PromoteToRoot's behaviour rather than leaving a
    dangling reference."""
    root = await employee_factory()
    child = await employee_factory(manager_id=root.id)

    policy = Reparent(db_session)
    result = await policy.apply(root.id, actor_id=actor_id)
    await db_session.commit()

    assert result.reassigned[0].id == child.id
    assert result.reassigned[0].manager_id is None


async def test_promote_to_root_makes_reports_roots(
    db_session, actor_id, employee_factory
):
    grandparent = await employee_factory()
    parent = await employee_factory(manager_id=grandparent.id)
    child = await employee_factory(manager_id=parent.id)

    policy = PromoteToRoot(db_session)
    result = await policy.apply(parent.id, actor_id=actor_id)
    await db_session.commit()

    assert [e.id for e in result.deleted] == [parent.id]
    assert result.reassigned[0].id == child.id
    assert result.reassigned[0].manager_id is None

    repo = EmployeeRepository(db_session)
    roots = await repo.get_roots()
    assert child.id in {e.id for e in roots}


async def test_cascade_deletes_entire_subtree(db_session, actor_id, employee_factory):
    root = await employee_factory()
    child = await employee_factory(manager_id=root.id)
    grandchild = await employee_factory(manager_id=child.id)
    unrelated = await employee_factory()

    policy = Cascade(db_session)
    affected = await preview(root.id, policy)
    assert {e.id for e in affected} == {root.id, child.id, grandchild.id}

    result = await policy.apply(root.id, actor_id=actor_id)
    await db_session.commit()

    assert {e.id for e in result.deleted} == {root.id, child.id, grandchild.id}

    repo = EmployeeRepository(db_session)
    assert await repo.get(root.id) is None
    assert await repo.get(child.id) is None
    assert await repo.get(grandchild.id) is None
    assert await repo.get(unrelated.id) is not None  # untouched


async def test_preview_does_not_write(db_session, actor_id, employee_factory):
    parent = await employee_factory()
    child = await employee_factory(manager_id=parent.id)

    for policy in (
        Reparent(db_session),
        PromoteToRoot(db_session),
        Cascade(db_session),
    ):
        await preview(parent.id, policy)

    repo = EmployeeRepository(db_session)
    fresh_parent = await repo.get(parent.id)
    fresh_child = await repo.get(child.id)
    assert fresh_parent is not None and fresh_parent.deleted_at is None
    assert fresh_child is not None and fresh_child.deleted_at is None
    assert fresh_child.manager_id == parent.id
