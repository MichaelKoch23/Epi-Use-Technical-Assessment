from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AssignmentNotFound,
    AssignmentOverlapError,
    DomainError,
    DuplicateEmailError,
    DuplicateEmployeeNumberError,
    EffectiveDateBeforeFirstAssignmentError,
    EmployeeNotFound,
    ReportingCycleError,
    ScheduledAssignmentInForceError,
    VersionConflictError,
)

_PROBLEMS: list[tuple[type[DomainError], int, str, str]] = [
    (EmployeeNotFound, 404, "employee-not-found", "Employee not found"),
    (
        DuplicateEmployeeNumberError,
        409,
        "duplicate-employee-number",
        "Employee number is already in use",
    ),
    (
        DuplicateEmailError,
        409,
        "duplicate-email",
        "Email is already in use",
    ),
    (
        VersionConflictError,
        409,
        "version-conflict",
        "The record changed since it was last read",
    ),
    (
        ReportingCycleError,
        422,
        "reporting-cycle",
        "Reassignment would create a reporting cycle",
    ),
    (AssignmentNotFound, 404, "assignment-not-found", "Assignment not found"),
    (
        ScheduledAssignmentInForceError,
        422,
        "scheduled-assignment-superseded",
        "The assignment is already in force",
    ),
    (
        AssignmentOverlapError,
        409,
        "assignment-overlap",
        "An assignment already covers that date",
    ),
    (
        EffectiveDateBeforeFirstAssignmentError,
        422,
        "effective-date-before-first-assignment",
        "Effective date precedes the first recorded assignment",
    ),
]
_DEFAULT = (500, "internal-error", "An unexpected error occurred")


def _problem_for(exc: DomainError) -> tuple[int, str, str]:
    for exc_type, status_code, slug, title in _PROBLEMS:
        if isinstance(exc, exc_type):
            return status_code, slug, title
    return _DEFAULT


def _field_errors(exc: DomainError) -> list[dict[str, str]]:
    if isinstance(exc, ReportingCycleError):
        return [{"field": "manager_id", "code": "cycle_detected"}]
    if isinstance(exc, DuplicateEmployeeNumberError):
        return [{"field": "employee_number", "code": "duplicate"}]
    if isinstance(exc, DuplicateEmailError):
        return [{"field": "email", "code": "duplicate"}]
    if isinstance(exc, VersionConflictError):
        return [{"field": "version", "code": "conflict"}]
    if isinstance(exc, EffectiveDateBeforeFirstAssignmentError):
        return [{"field": "effective_from", "code": "before_first_assignment"}]
    if isinstance(exc, AssignmentOverlapError):
        return [{"field": "effective_from", "code": "overlap"}]
    return []


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code, slug, title = _problem_for(exc)

    body: dict[str, object] = {
        "type": f"https://{request.base_url.hostname}/errors/{slug}",
        "title": title,
        "status": status_code,
        "detail": str(exc),
        "instance": request.url.path,
    }
    errors = _field_errors(exc)
    if errors:
        body["errors"] = errors

    return JSONResponse(
        status_code=status_code, content=body, media_type="application/problem+json"
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
