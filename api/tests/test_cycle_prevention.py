from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import ReportingCycleError
from app.services.reassignment_service import ReassignmentService


async def test_self_assignment_rejected(db_session, actor_id, employee_factory):
    employee = await employee_factory()
    service = ReassignmentService(db_session)

    with pytest.raises(ReportingCycleError) as exc_info:
        await service.reassign_manager(
            employee.id,
            employee.id,
            expected_version=employee.version,
            actor_id=actor_id,
        )

    assert exc_info.value.employee_id == employee.id
    assert exc_info.value.new_manager_id == employee.id


async def test_direct_inversion_rejected(db_session, actor_id, employee_factory):
    a = await employee_factory()
    b = await employee_factory(manager_id=a.id)
    service = ReassignmentService(db_session)

    with pytest.raises(ReportingCycleError) as exc_info:
        await service.reassign_manager(
            a.id, b.id, expected_version=a.version, actor_id=actor_id
        )

    assert exc_info.value.chain[0] == b.id
    assert a.id in exc_info.value.chain


async def _build_chain(employee_factory, length: int):
    root = await employee_factory()
    chain = [root]
    for _ in range(length):
        chain.append(await employee_factory(manager_id=chain[-1].id))
    return chain


@pytest.mark.parametrize("depth", [2, 3, 4, 5])
async def test_indirect_cycle_rejected(db_session, actor_id, employee_factory, depth):
    chain = await _build_chain(employee_factory, depth)
    root, descendant = chain[0], chain[-1]
    service = ReassignmentService(db_session)

    with pytest.raises(ReportingCycleError) as exc_info:
        await service.reassign_manager(
            root.id, descendant.id, expected_version=root.version, actor_id=actor_id
        )

    assert exc_info.value.employee_id == root.id
    assert exc_info.value.new_manager_id == descendant.id
    assert root.id in exc_info.value.chain
    assert descendant.id in exc_info.value.chain


async def test_reassignment_to_unrelated_branch_succeeds(
    db_session, actor_id, employee_factory
):
    branch_a_root = await employee_factory()
    a1 = await employee_factory(manager_id=branch_a_root.id)
    branch_b_root = await employee_factory()
    service = ReassignmentService(db_session)

    moved = await service.reassign_manager(
        a1.id, branch_b_root.id, expected_version=a1.version, actor_id=actor_id
    )
    await db_session.commit()

    assert moved.manager_id == branch_b_root.id


async def test_reassignment_to_null_succeeds(db_session, actor_id, employee_factory):
    manager = await employee_factory()
    report = await employee_factory(manager_id=manager.id)
    service = ReassignmentService(db_session)

    moved = await service.reassign_manager(
        report.id, None, expected_version=report.version, actor_id=actor_id
    )
    await db_session.commit()

    assert moved.manager_id is None


async def test_concurrent_inverse_reassignment_exactly_one_fails(
    session_factory, employee_factory
):
    a = await employee_factory()
    b = await employee_factory()

    async with session_factory() as tx1, session_factory() as tx2:
        await tx1.execute(
            text("UPDATE employee SET manager_id = :new_manager WHERE id = :id"),
            {"new_manager": b.id, "id": a.id},
        )
        await tx2.execute(
            text("UPDATE employee SET manager_id = :new_manager WHERE id = :id"),
            {"new_manager": a.id, "id": b.id},
        )

        await tx1.commit()

        with pytest.raises(DBAPIError, match="Reporting cycle detected"):
            await tx2.commit()
