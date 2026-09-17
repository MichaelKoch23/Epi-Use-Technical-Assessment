"""Avatar URL resolution (§ Gravatar avatars in the brand style guide):
uploaded override first, then a Gravatar image, with the client falling
back to initials only if that image itself 404s. Computed once here so
every response shape gets the same URL instead of each client re-hashing
the email."""

from __future__ import annotations

import hashlib
import re
import uuid

# Where `routers/avatars.py` serves uploaded pictures from. An override
# URL with this prefix is one of ours; anything else is an external link.
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
    """The `avatar_image` id an override URL points at, or None if the URL
    is empty or external."""
    if url is None:
        return None
    match = _UPLOADED_AVATAR_RE.match(url)
    return uuid.UUID(match.group(1)) if match else None


def resolve_avatar_url(*, avatar_override_url: str | None, email: str) -> str:
    return avatar_override_url or gravatar_url(email)
