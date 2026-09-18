from __future__ import annotations

import hashlib
import re
import uuid
from urllib.parse import urlencode

from app.core.config import settings

UPLOADED_AVATAR_PREFIX = "/api/v1/avatars/"

_UPLOADED_AVATAR_RE = re.compile(
    rf"^{re.escape(UPLOADED_AVATAR_PREFIX)}([0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}})$"
)


MAX_AVATAR_PX = 2048


def gravatar_hash(email: str) -> str:
    """SHA-256 of the trimmed, lower-cased address. Both steps are required."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def gravatar_url(email: str, size_px: int = 64) -> str:
    """Resolve an address to a Gravatar image URL.

    `d` decides what Gravatar serves when the address has no uploaded photo.
    With `d=404` nothing is served and the client falls back to initials, which
    is right for a real workforce but means a generated demo organisation shows
    no avatars at all. The setting lets a deployment choose: `identicon` and
    friends give every address a distinct generated image from Gravatar's CDN,
    `mp` gives everyone the same silhouette, `404` defers to the client.

    A real uploaded Gravatar always wins over the default, whichever is set.
    """
    size = max(1, min(size_px, MAX_AVATAR_PX))
    query = urlencode({"s": size, "d": settings.GRAVATAR_DEFAULT_IMAGE, "r": "pg"})
    return f"https://gravatar.com/avatar/{gravatar_hash(email)}?{query}"


def uploaded_avatar_url(image_id: uuid.UUID) -> str:
    return f"{UPLOADED_AVATAR_PREFIX}{image_id}"


def uploaded_avatar_id(url: str | None) -> uuid.UUID | None:
    if url is None:
        return None
    match = _UPLOADED_AVATAR_RE.match(url)
    return uuid.UUID(match.group(1)) if match else None


def resolve_avatar_url(*, avatar_override_url: str | None, email: str) -> str:
    return avatar_override_url or gravatar_url(email)
