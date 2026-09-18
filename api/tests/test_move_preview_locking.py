from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.services.assignment_service import AssignmentService, today


async def test_move_preview_takes_no_row_locks(
    db_session, session_factory, actor_id, employee_factory
):
    """A preview is a read, and every signed-in viewer can ask for one.

    It used to select the employee's future assignments FOR UPDATE, so an
    ordinary reader holding an open transaction could stall an administrator's
    reassignment. This pins that down: with a preview in flight, another
    session must still be able to lock those rows immediately.
    """
    manager = await employee_factory()
    other_manager = await employee_factory()
    mover = await employee_factory(manager_id=manager.id)

    await AssignmentService(db_session).reassign(
        mover.id,
        other_manager.id,
        effective_from=today() + timedelta(days=30),
        reason="Scheduled",
        actor_id=actor_id,
    )
    await db_session.commit()

    preview = await AssignmentService(db_session).preview_move(
        mover.id, other_manager.id, include_cost=True
    )
    assert len(preview.supersedes) == 1, "expected the scheduled move in the preview"

    async with session_factory() as other:
        try:
            await other.execute(
                text(
                    "SELECT 1 FROM employee_assignment"
                    " WHERE employee_id = :id FOR UPDATE NOWAIT"
                ),
                {"id": mover.id},
            )
        except DBAPIError as exc:  # pragma: no cover
            pytest.fail(f"move-preview is still holding row locks: {exc}")
        finally:
            await other.rollback()

    await db_session.rollback()
