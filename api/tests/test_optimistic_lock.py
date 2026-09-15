"""§5.4: concurrent edits must not silently overwrite one another. The
router layer (not built yet) maps `VersionConflictError` to `409
Conflict`; this test is the service-layer guarantee that error is built
on — two writes that both read the same version, the second of which
must be rejected rather than clobbering the first.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import VersionConflictError
from app.repositories.employee_repository import EmployeeRepository
from app.services.employee_service import EmployeeService


async def test_second_update_with_same_stale_version_is_rejected(
    db_session, actor_id, employee_factory
):
    employee = await employee_factory(position="Engineer")
    service = EmployeeService(db_session)

    # Two clients both loaded the employee at this version before either
    # submitted a change. Captured as plain values: `db_session.rollback()`
    # below expires the ORM instance, and touching its attributes after
    # that would trigger a lazy load outside of an async context.
    employee_id = employee.id
    submitted_version = employee.version

    first = await service.update(
        employee_id,
        expected_version=submitted_version,
        actor_id=actor_id,
        position="Senior Engineer",
    )
    await db_session.commit()
    assert first.version == submitted_version + 1
    assert first.position == "Senior Engineer"

    with pytest.raises(VersionConflictError) as exc_info:
        await service.update(
            employee_id,
            expected_version=submitted_version,
            actor_id=actor_id,
            position="Staff Engineer",
        )

    assert exc_info.value.employee_id == employee_id
    assert exc_info.value.expected_version == submitted_version
    assert exc_info.value.actual_version == submitted_version + 1

    # The rejected write must not have applied.
    await db_session.rollback()
    repo = EmployeeRepository(db_session)
    current = await repo.get(employee_id)
    assert current is not None
    assert current.position == "Senior Engineer"
    assert current.version == submitted_version + 1
