"""§5.3: the three deletion strategies, and the preview step the UI is
required to show before a destructive delete.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateEmailError, DuplicateEmployeeNumberError
from app.repositories.employee_repository import EmployeeRepository
from app.services.deletion_policy import Cascade, PromoteToRoot, Reparent, preview
from app.services.employee_service import EmployeeService


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


async def test_restore_reports_a_number_clash_instead_of_crashing(
    db_session, actor_id, employee_factory
):
    """`uq_employee_number` is a partial index (`WHERE deleted_at IS NULL`),
    so soft-deleting an employee releases their number for reuse. Restoring
    them afterwards collides, and the raw `IntegrityError` that Postgres
    raises at flush would otherwise reach the client as a 500."""
    original = await employee_factory(employee_number="E-REUSED")
    service = EmployeeService(db_session)
    await service.soft_delete(original.id, actor_id=actor_id)
    await db_session.commit()

    await employee_factory(employee_number="E-REUSED")  # number taken again

    with pytest.raises(DuplicateEmployeeNumberError):
        await service.restore(original.id, actor_id=actor_id)


async def test_restore_reports_an_email_clash_instead_of_crashing(
    db_session, actor_id, employee_factory
):
    original = await employee_factory(email="reused@example.com")
    service = EmployeeService(db_session)
    await service.soft_delete(original.id, actor_id=actor_id)
    await db_session.commit()

    await employee_factory(email="reused@example.com")

    with pytest.raises(DuplicateEmailError):
        await service.restore(original.id, actor_id=actor_id)


async def test_restore_succeeds_when_nothing_took_the_identifiers(
    db_session, actor_id, employee_factory
):
    """The guard must not block the ordinary case it was added for."""
    employee = await employee_factory(employee_number="E-FREE")
    service = EmployeeService(db_session)
    await service.soft_delete(employee.id, actor_id=actor_id)
    await db_session.commit()

    restored = await service.restore(employee.id, actor_id=actor_id)
    await db_session.commit()

    assert restored.deleted_at is None
