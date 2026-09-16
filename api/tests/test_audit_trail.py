"""§9.6: every mutating service writes its audit row inside the same unit
of work as the change itself, so the two can never disagree — either both
commit or neither does. Also covers the read side's salary redaction
(§9.3 extended to the audit trail): a viewer may see *that* salary
changed, never the value.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.pagination import PageParams
from app.core.security import Principal
from app.routers.employees import get_employee_audit
from app.services.audit_service import AuditService
from app.services.deletion_policy import Reparent
from app.services.employee_service import EmployeeService
from app.services.reassignment_service import ReassignmentService


async def test_create_writes_one_audit_row(db_session, actor_id, employee_factory):
    employee = await employee_factory()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee.id)
    assert total == 1
    assert rows[0].entry.action == "employee.created"
    assert rows[0].entry.before is None
    assert rows[0].entry.after is not None


async def test_update_writes_one_audit_row(db_session, actor_id, employee_factory):
    employee = await employee_factory(salary=Decimal(50000))
    service = EmployeeService(db_session)

    await service.update(
        employee.id,
        expected_version=employee.version,
        actor_id=actor_id,
        salary=Decimal(60000),
    )
    await db_session.commit()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee.id)
    assert total == 2
    latest = rows[0]  # newest first
    assert latest.entry.action == "employee.updated"
    assert latest.entry.before["salary"] == "50000"
    assert latest.entry.after["salary"] == "60000"


async def test_soft_delete_writes_one_audit_row(db_session, actor_id, employee_factory):
    employee = await employee_factory()

    await Reparent(db_session).apply(employee.id, actor_id=actor_id)
    await db_session.commit()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee.id)
    assert total == 2
    assert rows[0].entry.action == "employee.deleted"


async def test_restore_writes_one_audit_row(db_session, actor_id, employee_factory):
    employee = await employee_factory()
    service = EmployeeService(db_session)
    await service.soft_delete(employee.id, actor_id=actor_id)
    await db_session.commit()

    await service.restore(employee.id, actor_id=actor_id)
    await db_session.commit()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee.id)
    assert total == 3
    assert rows[0].entry.action == "employee.restored"


async def test_reassign_writes_one_audit_row(db_session, actor_id, employee_factory):
    manager = await employee_factory()
    employee = await employee_factory()
    service = ReassignmentService(db_session)

    await service.reassign_manager(
        employee.id, manager.id, expected_version=employee.version, actor_id=actor_id
    )
    await db_session.commit()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee.id)
    assert total == 2
    assert rows[0].entry.action == "employee.reassigned"
    assert rows[0].entry.after["manager_id"] == str(manager.id)


async def test_failed_update_rolls_back_its_audit_row(
    db_session, actor_id, employee_factory
):
    """The required rollback test: a legitimate update flushes its audit
    row (uncommitted), then a second write in the SAME transaction hits a
    real database constraint the service layer never pre-checks
    (`employee_salary_non_negative` — unlike `employee_number`/`email`,
    salary has no application-level guard, only the DB's own CHECK
    constraint, which only fires at flush). The whole transaction — the
    first update's audit row included — must disappear on rollback."""
    employee = await employee_factory(position="Engineer")
    # Captured as a plain value: `db_session.rollback()` below expires the
    # ORM instance, and touching its attributes after that would trigger a
    # lazy load outside of an async context (see test_optimistic_lock.py).
    employee_id = employee.id
    service = EmployeeService(db_session)

    updated = await service.update(
        employee_id,
        expected_version=employee.version,
        actor_id=actor_id,
        position="Senior Engineer",
    )

    with pytest.raises(IntegrityError):
        await service.update(
            employee_id,
            expected_version=updated.version,
            actor_id=actor_id,
            salary=Decimal(-1),
        )

    await db_session.rollback()

    audit = AuditService(db_session)
    rows, total = await audit.list_for_employee(employee_id)
    assert total == 1
    assert rows[0].entry.action == "employee.created"


async def test_audit_endpoint_redacts_salary_for_viewer(
    db_session, actor_id, employee_factory
):
    employee = await employee_factory(salary=Decimal(50000))
    service = EmployeeService(db_session)
    await service.update(
        employee.id,
        expected_version=employee.version,
        actor_id=actor_id,
        salary=Decimal(70000),
    )
    await db_session.commit()

    viewer = Principal(id=actor_id, role="viewer")
    page = await get_employee_audit(
        employee.id,
        pagination=PageParams(page=1, page_size=50),
        session=db_session,
        principal=viewer,
    )

    updated_entry = next(e for e in page.items if e.action == "employee.updated")
    assert updated_entry.salary_changed is True
    assert updated_entry.before is not None and "salary" not in updated_entry.before
    assert updated_entry.after is not None and "salary" not in updated_entry.after

    admin = Principal(id=actor_id, role="hr_admin")
    admin_page = await get_employee_audit(
        employee.id,
        pagination=PageParams(page=1, page_size=50),
        session=db_session,
        principal=admin,
    )
    admin_entry = next(e for e in admin_page.items if e.action == "employee.updated")
    assert admin_entry.salary_changed is True
    assert admin_entry.after is not None and admin_entry.after["salary"] == "70000"
