"""Reusable constrained field types for the write schemas (§9.4).

Validation here is deliberately the *outermost* layer of the same rules
the database already enforces, not a substitute for them: `salary >= 0`,
`birth_date > 1900-01-01` and `CHAR(3)` currency are all CHECK
constraints or column types in the schema. Restating them in Pydantic
turns what would otherwise be an `IntegrityError` surfacing as a 500 into
a 422 that names the offending field - the DB stays the authority, the
API stays honest about which input was wrong.

The length caps are the part the database does *not* have: `Text` columns
are unbounded, so without them a single request can push an arbitrary
number of megabytes into a row, and every subsequent read of that row
pays for it.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

# `salary NUMERIC(12, 2)` holds at most 10 integer digits; anything larger
# is a Postgres `numeric field overflow` (a 500) rather than a validation
# error, so the ceiling is stated here where it can be reported properly.
MAX_SALARY = Decimal("9999999999.99")

# Matches the `employee_birth_date_sane` CHECK constraint in migration
# 0fb48f633d33.
MIN_BIRTH_DATE = date(1900, 1, 1)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")
_ALLOWED_AVATAR_SCHEMES = ("http://", "https://")


def _validate_email(value: str) -> str:
    if not _EMAIL_RE.match(value):
        raise ValueError("must be a valid email address")
    return value


def _validate_birth_date(value: date) -> date:
    if value <= MIN_BIRTH_DATE:
        raise ValueError(f"must be after {MIN_BIRTH_DATE.isoformat()}")
    # The import path already blocks future birth dates (`_check_business_rules`);
    # without this the direct API would happily accept what a CSV of the same
    # rows is rejected for.
    if value > datetime.now(UTC).date():
        raise ValueError("must not be in the future")
    return value


def _validate_avatar_url(value: str | None) -> str | None:
    """An absolute `http(s)` URL, or nothing.

    This value is echoed back as `avatar_url` and rendered as an `<img
    src>` by every client. React escapes it, so this is not an XSS fix;
    the point is that without a scheme allow-list the field accepts
    `javascript:`, `data:` and `file:` URLs, which turns a personnel
    record into a stored redirect primitive aimed at whoever opens it.
    """
    if value is None:
        return None
    if not value.startswith(_ALLOWED_AVATAR_SCHEMES):
        raise ValueError("must be an absolute http:// or https:// URL")
    return value


# Spelled out one alias at a time rather than built by a helper: a factory
# returning `Annotated[...]` produces a value mypy sees as a variable, not a
# type, so every annotation using it becomes an error.
EmployeeNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]
PersonName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Position = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]

Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=320),
    AfterValidator(_validate_email),
]

BirthDate = Annotated[date, AfterValidator(_validate_birth_date)]

Salary = Annotated[Decimal, Field(ge=0, le=MAX_SALARY, decimal_places=2)]

Currency = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, pattern=_CURRENCY_RE),
]

AvatarOverrideUrl = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=2048),
    AfterValidator(_validate_avatar_url),
]
