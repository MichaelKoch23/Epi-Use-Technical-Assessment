"""Profile picture uploads: validate, normalise and store (§ Gravatar
avatars - the optional "upload" nice-to-have).

Every upload is decoded and re-encoded rather than stored as sent. That
is what makes serving it safe: the bytes that go back out are always a
WebP this code produced, so a file that merely *claims* to be an image
(an SVG with script, an HTML polyglot) never reaches a browser, and
camera EXIF metadata such as GPS coordinates is dropped on the way.
"""

from __future__ import annotations

import io
import uuid
import warnings

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.avatars import uploaded_avatar_id, uploaded_avatar_url
from app.models.app_user import AppUser
from app.models.avatar_image import AvatarImage
from app.models.employee import Employee

MAX_AVATAR_BYTES = 5 * 1024 * 1024
AVATAR_SIZE_PX = 512
_ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
# Decompression-bomb ceiling: a tiny file can declare enormous
# dimensions, and decoding it would allocate for all of them.
_MAX_SOURCE_PIXELS = 40_000_000
_OUTPUT_CONTENT_TYPE = "image/webp"


def normalise_image(raw: bytes) -> bytes:
    """Decode `raw`, centre-crop it square, scale it to `AVATAR_SIZE_PX`
    and re-encode as WebP. Raises a 422 for anything that isn't a
    supported, sanely sized image."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in _ACCEPTED_FORMATS:
                    raise _unsupported()
                if source.width * source.height > _MAX_SOURCE_PIXELS:
                    raise HTTPException(
                        status_code=422, detail="Image dimensions are too large"
                    )
                # Phone photos are often stored sideways with an EXIF
                # rotation flag; apply it before the flag is discarded.
                image = ImageOps.exif_transpose(source)
                image = image.convert("RGBA" if _has_alpha(image) else "RGB")
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
    ) as exc:
        raise _unsupported() from exc

    image = ImageOps.fit(
        image, (AVATAR_SIZE_PX, AVATAR_SIZE_PX), Image.Resampling.LANCZOS
    )
    out = io.BytesIO()
    image.save(out, format="WEBP", quality=85, method=4)
    return out.getvalue()


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info


def _unsupported() -> HTTPException:
    return HTTPException(
        status_code=422, detail="Upload a JPEG, PNG, WebP or GIF image"
    )


class AvatarService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(self, raw: bytes) -> str:
        """Normalise and persist an upload, returning the URL to set as an
        `avatar_override_url`."""
        image = AvatarImage(
            content_type=_OUTPUT_CONTENT_TYPE, data=normalise_image(raw)
        )
        self._session.add(image)
        await self._session.flush()
        return uploaded_avatar_url(image.id)

    async def get(self, image_id: uuid.UUID) -> AvatarImage | None:
        return await self._session.get(AvatarImage, image_id)

    async def discard_if_unused(self, url: str | None) -> None:
        """Delete the image behind a replaced or removed override URL once
        nothing refers to it any more. Called after the owning row has been
        updated (and flushed), so that row no longer counts as a reference.
        The URL can be copied onto another record through the edit form, so
        "unused" is checked rather than assumed."""
        image_id = uploaded_avatar_id(url)
        if image_id is None:
            return
        await self._session.flush()
        references = (
            await self._session.execute(
                select(func.count()).select_from(
                    select(Employee.id)
                    .where(Employee.avatar_override_url == url)
                    .union_all(
                        select(AppUser.id).where(AppUser.avatar_override_url == url)
                    )
                    .subquery()
                )
            )
        ).scalar_one()
        if references == 0:
            await self._session.execute(
                delete(AvatarImage).where(AvatarImage.id == image_id)
            )
