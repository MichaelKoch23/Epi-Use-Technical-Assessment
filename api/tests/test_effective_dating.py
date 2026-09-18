from __future__ import annotations

import itertools
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EffectiveDateBeforeFirstAssignmentError,
    ManagerUnchangedError,
    ReportingCycleError,
    ScheduledAssignmentInForceError,
)
from app.repositories.assignment_repository import AssignmentRepository
from app.services.assignment_service import AssignmentService
from app.services.employee_service import EmployeeService
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

    with pytest.raises(ReportingCycleError) as exc:
        await service.reassign(
            a.id, b.id, effective_from=september, reason="A under B", actor_id=actor_id
        )
    assert exc.value.at == october
    assert b.id in exc.value.chain
    await db_session.rollback()


async def test_the_same_move_is_allowed_when_nothing_is_scheduled(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """The control for the flagship case above.

    Identical move, identical dates, but with no scheduled change to close the
    loop - it succeeds. That is what shows the rejection came from the future
    edge rather than from anything about the move itself.
    """
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)

    result = await AssignmentService(db_session).reassign(
        a.id,
        b.id,
        effective_from=TODAY + timedelta(days=30),
        reason="A under B",
        actor_id=actor_id,
    )
    await db_session.commit()
    assert result.assignment.manager_id == b.id


async def test_reassigning_to_the_current_manager_is_rejected(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """A move to the manager already in force is a non-change, not a move.

    Allowing it closes the open run and opens an identical one, so the history
    reads "moved from Ravi to Ravi" and the audit log gains an entry for
    something that never happened.
    """
    root = await employee_factory()
    manager = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=manager.id)

    mover_id, manager_id = mover.id, manager.id
    before = await _count(db_session)
    with pytest.raises(ManagerUnchangedError):
        await AssignmentService(db_session).reassign(
            mover_id, manager_id, actor_id=actor_id
        )

    assert await _count(db_session) == before
    rows = await AssignmentRepository(db_session).get_assignment_history(mover_id)
    assert [row.assignment.manager_id for row in rows] == [manager_id]


async def test_reaffirming_the_current_manager_calls_off_a_scheduled_move(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """The exception to the rule above, and why it is not a blanket rejection."""
    root = await employee_factory()
    manager = await employee_factory(manager_id=root.id)
    other = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=manager.id)

    service = AssignmentService(db_session)
    scheduled = await service.reassign(
        mover.id,
        other.id,
        effective_from=TODAY + timedelta(days=20),
        reason="planned",
        actor_id=actor_id,
    )
    await db_session.commit()

    result = await service.reassign(
        mover.id, manager.id, reason="staying put", actor_id=actor_id
    )
    await db_session.commit()

    assert scheduled.assignment.id in [c.id for c in result.cancelled]
    assert await AssignmentRepository(db_session).get_scheduled() == []


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


async def test_a_departure_ends_on_its_date_rather_than_rewriting_history(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """Deleting somebody removes them from that day on, not from all of time.

    The whole point of the as-at view is that yesterday still reads the way it
    read yesterday. A departure is dated like any other change: gone from the
    day it happens, present on every day before it.
    """
    ceo = await employee_factory()
    manager = await employee_factory(manager_id=ceo.id)
    ic = await employee_factory(manager_id=manager.id)
    yesterday = TODAY - timedelta(days=1)

    # Backdate the opening runs so there is a day of history to read.
    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :from_date"),
        {"from_date": TODAY - timedelta(days=30)},
    )
    await db_session.commit()

    await EmployeeService(db_session).soft_delete(manager.id, actor_id=actor_id)
    await db_session.commit()

    repo = AssignmentRepository(db_session)

    rows = await repo.get_tree(yesterday)
    by_id = {row.employee.id: row for row in rows}
    assert manager.id in by_id, "yesterday predates the deletion"
    assert by_id[manager.id].employee.manager_id == ceo.id
    assert by_id[ic.id].depth == 2, "the branch still hangs off the manager"

    today_ids = {row.employee.id for row in await repo.get_tree(TODAY)}
    assert manager.id not in today_ids
    assert {ceo.id, ic.id} <= today_ids


async def test_an_edge_left_pointing_at_a_departed_manager_does_not_strand_a_branch(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """The guard in the root CTE, exercised.

    Deleting through a DeletionPolicy reparents the reports, so their edge
    never outlives their manager. soft_delete on its own does not, which is
    the shape of any row written before departures were dated: without the
    guard that branch falls out of the tree entirely, and the view comes back
    empty when the departed manager was the only root.
    """
    manager = await employee_factory()
    ic = await employee_factory(manager_id=manager.id)

    await EmployeeService(db_session).soft_delete(manager.id, actor_id=actor_id)
    await db_session.commit()

    repo = AssignmentRepository(db_session)
    rows = await repo.get_tree(TODAY)
    assert manager.id not in {row.employee.id for row in rows}
    assert ic.id in {row.employee.id for row in rows}

    roots = await repo.get_tree(TODAY, max_depth=0)
    assert ic.id in {row.employee.id for row in roots}


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


async def _insert_assignment(
    session: AsyncSession,
    employee_id: uuid.UUID,
    manager_id: uuid.UUID | None,
    valid_from: date,
    valid_to: date | None = None,
) -> None:
    await session.execute(
        text(
            "INSERT INTO employee_assignment"
            " (employee_id, manager_id, valid_from, valid_to)"
            " VALUES (:e, :m, :f, :t)"
        ),
        {"e": employee_id, "m": manager_id, "f": valid_from, "t": valid_to},
    )


async def test_exclusion_constraint_rejects_an_overlapping_assignment(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    """An employee can never have two managers on the same day."""
    root = await employee_factory()
    other = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=root.id)
    await db_session.commit()

    with pytest.raises(IntegrityError) as exc:
        async with db_session.begin_nested():
            await _insert_assignment(db_session, mover.id, other.id, TODAY)
    assert "assignment_no_overlap" in str(exc.value.orig)


async def test_exclusion_constraint_permits_an_adjacent_assignment(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    """valid_to is the first day NOT in force, so touching ranges do not overlap."""
    root = await employee_factory()
    other = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=root.id)

    handover = TODAY + timedelta(days=30)
    await db_session.execute(
        text("UPDATE employee_assignment SET valid_to = :t WHERE employee_id = :e"),
        {"t": handover, "e": mover.id},
    )
    await _insert_assignment(db_session, mover.id, other.id, handover)
    await db_session.commit()

    rows = await AssignmentRepository(db_session).get_assignment_history(mover.id)
    assert [r.assignment.valid_from for r in rows] == [handover, TODAY]
    assert rows[1].assignment.valid_to == rows[0].assignment.valid_from


async def test_exclusion_constraint_is_scoped_to_one_employee(
    db_session: AsyncSession, employee_factory: EmployeeFactory
) -> None:
    """Two different people may of course both have a manager today."""
    root = await employee_factory()
    first = await employee_factory(manager_id=root.id)
    second = await employee_factory(manager_id=root.id)
    await db_session.commit()

    before = await _count(db_session)
    await db_session.execute(
        text("DELETE FROM employee_assignment WHERE employee_id IN (:a, :b)"),
        {"a": first.id, "b": second.id},
    )
    await _insert_assignment(db_session, first.id, root.id, TODAY)
    await _insert_assignment(db_session, second.id, root.id, TODAY)
    await db_session.commit()
    assert await _count(db_session) == before


async def test_get_tree_returns_the_structure_as_it_stood_at_four_dates(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """Three moves, four dates, four different answers."""
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    c = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)

    opened = TODAY - timedelta(days=400)
    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :d WHERE employee_id = :e"),
        {"d": opened, "e": mover.id},
    )

    service = AssignmentService(db_session)
    moves = [
        (b.id, TODAY - timedelta(days=300), "to B"),
        (c.id, TODAY - timedelta(days=200), "to C"),
        (a.id, TODAY - timedelta(days=100), "back to A"),
    ]
    for manager_id, effective_from, reason in moves:
        await service.reassign(
            mover.id,
            manager_id,
            effective_from=effective_from,
            reason=reason,
            actor_id=actor_id,
        )
    await db_session.commit()

    repo = AssignmentRepository(db_session)

    async def manager_at(as_of: date) -> uuid.UUID | None:
        rows = await repo.get_tree(as_of)
        return next(r.employee.manager_id for r in rows if r.employee.id == mover.id)

    assert await manager_at(TODAY - timedelta(days=350)) == a.id
    assert await manager_at(TODAY - timedelta(days=250)) == b.id
    assert await manager_at(TODAY - timedelta(days=150)) == c.id
    assert await manager_at(TODAY) == a.id

    history = [r.assignment for r in await repo.get_assignment_history(mover.id)]
    assert [row.valid_from for row in history] == [
        TODAY - timedelta(days=100),
        TODAY - timedelta(days=200),
        TODAY - timedelta(days=300),
        opened,
    ]
    assert history[0].valid_to is None
    for newer, older in itertools.pairwise(history):
        assert older.valid_to == newer.valid_from


async def test_the_boundary_day_itself_belongs_to_the_new_manager(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """'[)' means the effective date is the new manager's first day, not the old one's last."""
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)

    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :d WHERE employee_id = :e"),
        {"d": TODAY - timedelta(days=90), "e": mover.id},
    )
    changeover = TODAY - timedelta(days=30)
    await AssignmentService(db_session).reassign(
        mover.id, b.id, effective_from=changeover, reason="moved", actor_id=actor_id
    )
    await db_session.commit()

    repo = AssignmentRepository(db_session)

    async def manager_at(as_of: date) -> uuid.UUID | None:
        rows = await repo.get_tree(as_of)
        return next(r.employee.manager_id for r in rows if r.employee.id == mover.id)

    assert await manager_at(changeover - timedelta(days=1)) == a.id
    assert await manager_at(changeover) == b.id


async def test_a_scheduled_change_applies_itself_once_its_date_arrives(
    db_session: AsyncSession, employee_factory: EmployeeFactory, actor_id: uuid.UUID
) -> None:
    """Advance the world past a scheduled date and sync applies it.

    sync_effective_assignments() reads CURRENT_DATE inside the database, so the
    test cannot move the clock the process sees. Shifting the employee's rows
    back by the same interval produces exactly the row state the database would
    hold once that date arrived, which is what the function reacts to.
    """
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)
    await db_session.commit()

    service = AssignmentService(db_session)
    repo = AssignmentRepository(db_session)
    horizon = 30
    await service.reassign(
        mover.id,
        b.id,
        effective_from=TODAY + timedelta(days=horizon),
        reason="planned",
        actor_id=actor_id,
    )
    await db_session.commit()

    await db_session.refresh(mover)
    version_while_pending = mover.version
    assert mover.manager_id == a.id
    assert await repo.sync_effective(force=True) == 0

    await db_session.execute(
        text(
            "UPDATE employee_assignment"
            " SET valid_from = valid_from - make_interval(days => :d),"
            "     valid_to   = valid_to   - make_interval(days => :d)"
            " WHERE employee_id = :e"
        ),
        {"d": horizon, "e": mover.id},
    )
    await db_session.commit()

    assert await repo.sync_effective(force=True) == 1
    await db_session.commit()

    await db_session.refresh(mover)
    assert mover.manager_id == b.id
    assert mover.version == version_while_pending + 1
    assert await repo.get_scheduled() == []
    assert await repo.sync_effective(force=True) == 0
