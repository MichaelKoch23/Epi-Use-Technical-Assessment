from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.avatars import gravatar_hash
from app.core.config import settings

GRAVATAR_API_BASE = "https://api.gravatar.com/v3"


@dataclass(frozen=True, slots=True)
class GravatarProfile:
    """The subset of a Gravatar profile worth prefilling an employee form with."""

    hash: str
    display_name: str | None
    first_name: str | None
    last_name: str | None
    job_title: str | None
    company: str | None
    location: str | None
    description: str | None
    profile_url: str | None
    avatar_url: str | None


def _split_name(display_name: str | None) -> tuple[str | None, str | None]:
    if not display_name:
        return None, None
    parts = display_name.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


class GravatarClient:
    """Reads public Gravatar profiles.

    The key is optional: an unauthenticated request still returns a profile, just
    a thinner one. Every failure resolves to None rather than raising, because a
    prefill suggestion is a convenience and must never be able to fail a request.
    """

    def __init__(
        self, api_key: str | None = None, timeout: float | None = None
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GRAVATAR_API_KEY
        self._timeout = (
            timeout if timeout is not None else settings.GRAVATAR_API_TIMEOUT_SECONDS
        )

    async def get_profile(self, email: str) -> GravatarProfile | None:
        digest = gravatar_hash(email)
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{GRAVATAR_API_BASE}/profiles/{digest}", headers=headers
                )
        except httpx.HTTPError:
            return None

        # 404 simply means the address has no Gravatar, which is not an error.
        if response.status_code != 200:
            return None

        try:
            body = response.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None

        display_name = body.get("display_name")
        first_name, last_name = _split_name(display_name)
        return GravatarProfile(
            hash=digest,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            job_title=body.get("job_title"),
            company=body.get("company"),
            location=body.get("location"),
            description=body.get("description"),
            profile_url=body.get("profile_url"),
            avatar_url=body.get("avatar_url"),
        )
