from __future__ import annotations

import uuid

from pydantic import BaseModel


class SearchResultRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    position: str
    employee_number: str
    avatar_url: str
