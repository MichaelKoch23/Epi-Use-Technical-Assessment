from __future__ import annotations

import uuid
from collections.abc import Sequence


class DomainError(Exception):
    """Base class for exceptions raised by the service layer.

    A single exception-handler layer maps these to RFC 9457 problem
    documents (§6.4); nothing below the service layer should raise or
    catch them, and routers should catch nothing more specific.
    """


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
    """Raised when a write's `expected_version` no longer matches the
    row's current `version` — another change landed first (§5.4)."""

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
    """Raised when a proposed manager assignment would create a reporting
    cycle. `chain` is the existing reporting path from the proposed
    manager up to the employee being reassigned — the path that the
    assignment would close into a loop (§5.2, §6.4)."""

    def __init__(
        self,
        employee_id: uuid.UUID,
        new_manager_id: uuid.UUID,
        chain: Sequence[uuid.UUID],
    ) -> None:
        self.employee_id = employee_id
        self.new_manager_id = new_manager_id
        self.chain = list(chain)
        super().__init__(
            f"Assigning {new_manager_id} as manager of {employee_id} would create "
            f"a reporting cycle: {' -> '.join(str(step) for step in self.chain)}"
        )
