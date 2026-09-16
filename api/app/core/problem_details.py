"""A single exception handler mapping domain exceptions (`core.exceptions`)
to RFC 9457 `application/problem+json` documents (§6.4). Registered once
for the `DomainError` base class — Starlette walks the MRO of a raised
exception to find the most specific handler, so this one function catches
every subclass without a handler per exception type."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DomainError,
    DuplicateEmailError,
    DuplicateEmployeeNumberError,
    EmployeeNotFound,
    ReportingCycleError,
    VersionConflictError,
)

# exception type -> (status, URI slug, title)
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
    return []


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # the only type this handler is registered for
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
