from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EffectiveDateBeforeFirstAssignmentError,
    ReportingCycleError,
    ScheduledAssignmentInForceError,
)
from app.repositories.assignment_repository import AssignmentRepository
from app.services.assignment_service import AssignmentService
from tests.conftest import EmployeeFactory

TODAY = datetime.now(UTC).date()


async def _count(session: AsyncSession) -> int:
    return (
        await session.execute(text("SELECT count(*) FROM employee_assignment"))
    ).scalar_one()


async def test_create_opens_an_assignment_run(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    ceo = await employee_factory()
    ic = await employee_factory(manager_id=ceo.id)
    repo = AssignmentRepository(db_session)
    rows = await repo.get_assignment_history(ic.id)
    assert len(rows) == 1
    assert rows[0].assignment.manager_id == ceo.id
    assert rows[0].assignment.valid_to is None


async def test_as_of_tree_reflects_history_not_the_cache(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    ceo = await employee_factory()
    a = await employee_factory(manager_id=ceo.id)
    b = await employee_factory(manager_id=ceo.id)
    mover = await employee_factory(manager_id=a.id)

    service = AssignmentService(db_session)
    # Backdate the mover's first run so a past date is representable.
    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :d WHERE employee_id = :e"),
        {"d": TODAY - timedelta(days=200), "e": mover.id},
    )
    await service.reassign(
        mover.id,
        b.id,
        effective_from=TODAY - timedelta(days=30),
        reason="moved",
        actor_id=actor_id,
    )
    await db_session.commit()

    repo = AssignmentRepository(db_session)
    before = {
        r.employee.id: r.employee.manager_id
        for r in await repo.get_tree(TODAY - timedelta(days=100))
    }
    after = {r.employee.id: r.employee.manager_id for r in await repo.get_tree(TODAY)}
    assert before[mover.id] == a.id
    assert after[mover.id] == b.id


async def test_future_dated_change_is_invisible_today(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    ceo = await employee_factory()
    a = await employee_factory(manager_id=ceo.id)
    b = await employee_factory(manager_id=ceo.id)
    mover = await employee_factory(manager_id=a.id)

    service = AssignmentService(db_session)
    future = TODAY + timedelta(days=30)
    result = await service.reassign(
        mover.id, b.id, effective_from=future, reason="planned", actor_id=actor_id
    )
    await db_session.commit()
    assert result.in_force_now is False

    repo = AssignmentRepository(db_session)
    today_tree = {
        r.employee.id: r.employee.manager_id for r in await repo.get_tree(TODAY)
    }
    future_tree = {
        r.employee.id: r.employee.manager_id for r in await repo.get_tree(future)
    }
    assert today_tree[mover.id] == a.id
    assert future_tree[mover.id] == b.id
    assert await repo.sync_effective(force=True) == 0

    await db_session.refresh(mover)
    assert mover.manager_id == a.id
    assert len(await service.get_scheduled()) == 1


async def test_temporal_cycle_across_a_scheduled_change(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """The flagship case: fine on the day, cyclic once a later change lands."""
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)

    service = AssignmentService(db_session)
    october = TODAY + timedelta(days=60)
    september = TODAY + timedelta(days=30)

    await service.reassign(
        b.id, a.id, effective_from=october, reason="B under A", actor_id=actor_id
    )
    await db_session.commit()

    # At september the structure is acyclic, so a point-in-time check would allow
    # this. At october it would close a loop.
    with pytest.raises(ReportingCycleError) as exc:
        await service.reassign(
            a.id, b.id, effective_from=september, reason="A under B", actor_id=actor_id
        )
    assert exc.value.at == october
    assert b.id in exc.value.chain
    await db_session.rollback()


async def test_move_supersedes_scheduled_and_reports_them(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)

    service = AssignmentService(db_session)
    planned = TODAY + timedelta(days=20)
    first = await service.reassign(
        mover.id, b.id, effective_from=planned, reason="planned", actor_id=actor_id
    )
    await db_session.commit()

    second = await service.reassign(
        mover.id,
        root.id,
        effective_from=TODAY + timedelta(days=10),
        reason="changed our minds",
        actor_id=actor_id,
    )
    await db_session.commit()
    assert [c.id for c in second.cancelled] == [first.assignment.id]

    repo = AssignmentRepository(db_session)
    assert len(await repo.get_scheduled()) == 1


async def test_preview_writes_nothing(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    await employee_factory(manager_id=a.id)
    await employee_factory(manager_id=a.id)
    await db_session.commit()

    before = await _count(db_session)
    service = AssignmentService(db_session)
    preview = await service.preview_move(a.id, b.id, include_cost=True)
    await db_session.commit()

    assert await _count(db_session) == before
    assert preview.headcount == 3
    assert preview.depth_change == 1
    assert preview.blocked is False
    assert preview.cost is not None
    assert preview.cost.leaving == preview.cost.arriving > 0

    viewer_preview = await service.preview_move(a.id, b.id, include_cost=False)
    assert viewer_preview.cost is None


async def test_preview_reports_blocked_for_a_cyclic_move(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    child = await employee_factory(manager_id=a.id)
    await db_session.commit()

    preview = await AssignmentService(db_session).preview_move(
        a.id, child.id, include_cost=True
    )
    assert preview.blocked is True
    assert preview.blocked_chain[0] == child.id


async def test_cancel_scheduled_reopens_the_preceding_run(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)

    service = AssignmentService(db_session)
    scheduled = await service.reassign(
        mover.id,
        b.id,
        effective_from=TODAY + timedelta(days=15),
        reason="planned",
        actor_id=actor_id,
    )
    await db_session.commit()

    await service.cancel_scheduled(scheduled.assignment.id, actor_id=actor_id)
    await db_session.commit()

    repo = AssignmentRepository(db_session)
    history = await repo.get_assignment_history(mover.id)
    assert len(history) == 1
    assert history[0].assignment.manager_id == a.id
    assert history[0].assignment.valid_to is None
    assert await repo.get_scheduled() == []


async def test_cancel_refuses_an_assignment_already_in_force(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    root = await employee_factory()
    mover = await employee_factory(manager_id=root.id)
    await db_session.commit()

    repo = AssignmentRepository(db_session)
    current = (await repo.get_assignment_history(mover.id))[0].assignment
    with pytest.raises(ScheduledAssignmentInForceError):
        await AssignmentService(db_session).cancel_scheduled(
            current.id, actor_id=actor_id
        )


async def test_effective_date_before_the_first_assignment_is_refused(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    root = await employee_factory()
    other = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=root.id)
    await db_session.commit()

    with pytest.raises(EffectiveDateBeforeFirstAssignmentError):
        await AssignmentService(db_session).reassign(
            mover.id,
            other.id,
            effective_from=date(2019, 1, 1),
            reason="too early",
            actor_id=actor_id,
        )


async def test_diff_structure_reads_from_assignments_alone(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)
    await employee_factory(manager_id=mover.id)

    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :d"),
        {"d": TODAY - timedelta(days=300)},
    )
    service = AssignmentService(db_session)
    await service.reassign(
        mover.id,
        b.id,
        effective_from=TODAY - timedelta(days=10),
        reason="moved",
        actor_id=actor_id,
    )
    await db_session.commit()

    diff = await service.diff_structure(TODAY - timedelta(days=100), TODAY)
    assert [c.employee_id for c in diff.manager_changes] == [mover.id]
    assert diff.manager_changes[0].from_manager_id == a.id
    assert diff.manager_changes[0].to_manager_id == b.id
    assert diff.manager_changes[0].from_manager_name is not None
    assert [c.employee_id for c in diff.branch_moves] == [mover.id]
    assert diff.became_root == []
    assert diff.max_depth_from == diff.max_depth_to == 3
