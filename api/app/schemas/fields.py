from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

from app.core.avatars import uploaded_avatar_id

MAX_SALARY = Decimal("9999999999.99")

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
    if value > datetime.now(UTC).date():
        raise ValueError("must not be in the future")
    return value


def _validate_avatar_url(value: str | None) -> str | None:
    if value is None:
        return None
    if uploaded_avatar_id(value) is not None:
        return value
    if not value.startswith(_ALLOWED_AVATAR_SCHEMES):
        raise ValueError("must be an absolute http:// or https:// URL")
    return value


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

ReassignReason = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=500),
]

AvatarOverrideUrl = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=2048),
    AfterValidator(_validate_avatar_url),
]
