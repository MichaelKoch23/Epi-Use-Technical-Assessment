from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ImportRowOutcome = Literal["will_create", "will_update", "blocked"]


class ImportRowResult(BaseModel):
    row_number: int
    employee_number: str | None
    name: str | None
    outcome: ImportRowOutcome
    reason: str | None


class ImportResult(BaseModel):
    rows: list[ImportRowResult]
    created: int
    updated: int
    blocked: int
    committed: bool
