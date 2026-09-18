from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date


class DomainError(Exception):
    pass


class EmployeeNotFound(DomainError):
    def __init__(self, employee_id: uuid.UUID) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id} not found")


class DuplicateEmployeeNumberError(DomainError):
    def __init__(self, employee_number: str) -> None:
        self.employee_number = employee_number
        super().__init__(f"Employee number {employee_number!r} is already in use")


class DuplicateEmailError(DomainError):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email {email!r} is already in use")


class VersionConflictError(DomainError):
    def __init__(
        self, employee_id: uuid.UUID, expected_version: int, actual_version: int
    ) -> None:
        self.employee_id = employee_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Employee {employee_id} is at version {actual_version}, but the "
            f"request expected version {expected_version}"
        )


class ReportingCycleError(DomainError):
    def __init__(
        self,
        employee_id: uuid.UUID,
        new_manager_id: uuid.UUID,
        chain: Sequence[uuid.UUID],
        *,
        at: date | None = None,
    ) -> None:
        self.employee_id = employee_id
        self.new_manager_id = new_manager_id
        self.chain = list(chain)
        self.at = at
        when = f" as at {at.isoformat()}" if at is not None else ""
        super().__init__(
            f"Assigning {new_manager_id} as manager of {employee_id} would create "
            f"a reporting cycle{when}: "
            f"{' -> '.join(str(step) for step in self.chain)}"
        )


class ManagerUnchangedError(DomainError):
    """The requested manager is already the one in force, with nothing pending.

    Writing it anyway would close the open run and open an identical one, so
    the history would show a move from a manager to themselves and the audit
    log would record a change that never happened.
    """

    def __init__(self, employee_id: uuid.UUID, manager_id: uuid.UUID | None) -> None:
        self.employee_id = employee_id
        self.manager_id = manager_id
        target = "have no manager" if manager_id is None else "report to that manager"
        super().__init__(
            f"This employee already {target} from that date, "
            "so there is nothing to change"
        )


class AssignmentNotFound(DomainError):
    def __init__(self, assignment_id: uuid.UUID) -> None:
        self.assignment_id = assignment_id
        super().__init__(f"Assignment {assignment_id} not found")


class ScheduledAssignmentInForceError(DomainError):
    def __init__(self, assignment_id: uuid.UUID, valid_from: date) -> None:
        self.assignment_id = assignment_id
        self.valid_from = valid_from
        super().__init__(
            f"Assignment {assignment_id} took effect on {valid_from.isoformat()} "
            "and is already in force, so it can no longer be cancelled"
        )


class AssignmentOverlapError(DomainError):
    def __init__(self, employee_id: uuid.UUID, effective_from: date) -> None:
        self.employee_id = employee_id
        self.effective_from = effective_from
        super().__init__(
            f"An assignment for employee {employee_id} already covers "
            f"{effective_from.isoformat()}"
        )


class EffectiveDateBeforeFirstAssignmentError(DomainError):
    def __init__(
        self, employee_id: uuid.UUID, effective_from: date, earliest: date
    ) -> None:
        self.employee_id = employee_id
        self.effective_from = effective_from
        self.earliest = earliest
        super().__init__(
            f"Effective date {effective_from.isoformat()} precedes the first "
            f"recorded assignment for employee {employee_id} "
            f"({earliest.isoformat()})"
        )
