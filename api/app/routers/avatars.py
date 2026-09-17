from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.avatar_service import AvatarService

router = APIRouter(prefix="/api/v1/avatars", tags=["avatars"])


@router.get(
    "/{image_id}",
    response_class=Response,
    responses={200: {"content": {"image/webp": {}}}},
)
async def get_avatar(
    image_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> Response:
    image = await AvatarService(session).get(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return Response(
        content=image.data,
        media_type=image.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
