"""Avatar URL resolution (§ Gravatar avatars in the brand style guide):
uploaded override first, then a Gravatar image, with the client falling
back to initials only if that image itself 404s. Computed once here so
every response shape gets the same URL instead of each client re-hashing
the email."""

from __future__ import annotations

import hashlib


def gravatar_url(email: str, size_px: int = 64) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return f"https://gravatar.com/avatar/{digest}?s={size_px}&d=404"


def resolve_avatar_url(*, avatar_override_url: str | None, email: str) -> str:
    return avatar_override_url or gravatar_url(email)
