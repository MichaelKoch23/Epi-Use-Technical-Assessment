from __future__ import annotations

import uuid

from pydantic import BaseModel


class SearchResultRead(BaseModel):
    """A command-palette result. Deliberately lighter than `EmployeeRead` -
    no salary concern applies here since the field was never selected in
    the first place, not merely omitted from the response."""

    id: uuid.UUID
    first_name: str
    last_name: str
    position: str
    employee_number: str
    avatar_url: str
