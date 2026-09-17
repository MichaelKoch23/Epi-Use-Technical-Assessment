from __future__ import annotations

import hashlib
import re
import uuid

UPLOADED_AVATAR_PREFIX = "/api/v1/avatars/"

_UPLOADED_AVATAR_RE = re.compile(
    rf"^{re.escape(UPLOADED_AVATAR_PREFIX)}([0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}})$"
)


def gravatar_url(email: str, size_px: int = 64) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return f"https://gravatar.com/avatar/{digest}?s={size_px}&d=404"


def uploaded_avatar_url(image_id: uuid.UUID) -> str:
    return f"{UPLOADED_AVATAR_PREFIX}{image_id}"


def uploaded_avatar_id(url: str | None) -> uuid.UUID | None:
    if url is None:
        return None
    match = _UPLOADED_AVATAR_RE.match(url)
    return uuid.UUID(match.group(1)) if match else None


def resolve_avatar_url(*, avatar_override_url: str | None, email: str) -> str:
    return avatar_override_url or gravatar_url(email)
