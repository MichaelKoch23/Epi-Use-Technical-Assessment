from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.gravatar import GravatarClient, _split_name
from app.core.avatars import (
    MAX_AVATAR_PX,
    gravatar_hash,
    gravatar_url,
    resolve_avatar_url,
)
from app.core.config import settings

TUTORIAL_EMAIL = "sarahthompson@fork.do"
TUTORIAL_HASH = "03f35cb0038f321f291113ba702c0b0574b9d64de93617c0b66b3504fe393152"


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def test_hash_matches_gravatars_published_example() -> None:
    assert gravatar_hash(TUTORIAL_EMAIL) == TUTORIAL_HASH


@pytest.mark.parametrize(
    "variant",
    ["  sarahthompson@fork.do  ", "SarahThompson@Fork.DO", "SARAHTHOMPSON@FORK.DO"],
)
def test_hash_trims_and_lowercases(variant: str) -> None:
    assert gravatar_hash(variant) == TUTORIAL_HASH


def test_url_carries_the_hash_not_the_address() -> None:
    url = gravatar_url(TUTORIAL_EMAIL)
    assert TUTORIAL_HASH in url
    assert "sarahthompson" not in url


def test_default_image_comes_from_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """d=404 serves nothing and the client draws initials; identicon serves an image.

    A generated demo organisation has no real photos, so the difference decides
    whether every employee shows an avatar or none of them do.
    """
    monkeypatch.setattr(settings, "GRAVATAR_DEFAULT_IMAGE", "identicon")
    assert _query(gravatar_url(TUTORIAL_EMAIL))["d"] == ["identicon"]

    monkeypatch.setattr(settings, "GRAVATAR_DEFAULT_IMAGE", "404")
    assert _query(gravatar_url(TUTORIAL_EMAIL))["d"] == ["404"]


def test_rating_is_pinned_to_pg() -> None:
    assert _query(gravatar_url(TUTORIAL_EMAIL))["r"] == ["pg"]


def test_requested_size_is_capped() -> None:
    assert _query(gravatar_url(TUTORIAL_EMAIL, 99_999))["s"] == [str(MAX_AVATAR_PX)]
    assert _query(gravatar_url(TUTORIAL_EMAIL, 128))["s"] == ["128"]


def test_an_uploaded_photo_wins_over_gravatar() -> None:
    resolved = resolve_avatar_url(
        avatar_override_url="/api/v1/avatars/x", email=TUTORIAL_EMAIL
    )
    assert resolved == "/api/v1/avatars/x"


@pytest.mark.parametrize(
    ("display_name", "expected"),
    [
        ("Sarah Thompson", ("Sarah", "Thompson")),
        ("Riaan van der Merwe", ("Riaan", "van der Merwe")),
        ("Cher", ("Cher", None)),
        (None, (None, None)),
        ("", (None, None)),
    ],
)
def test_display_names_split_into_first_and_last(
    display_name: str | None, expected: tuple[str | None, str | None]
) -> None:
    assert _split_name(display_name) == expected


async def test_profile_lookup_returns_none_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enrichment is a convenience, so an unreachable Gravatar must not surface."""
    import httpx

    async def boom(*args: object, **kwargs: object) -> object:
        raise httpx.ConnectError("gravatar is down")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    assert await GravatarClient(api_key="").get_profile(TUTORIAL_EMAIL) is None
