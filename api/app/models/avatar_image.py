import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AvatarImage(Base):
    """An uploaded profile picture, already re-encoded by `avatar_service`.

    Kept in Postgres rather than on disk: the container's filesystem is
    read-only and ephemeral on Cloud Run, and the brief requires every
    modification to land in the remote database. A re-encoded 512px WebP
    is a few tens of kilobytes, well inside what `bytea` handles comfortably.
    Rows are immutable - a new upload is a new row (and a new URL), which is
    what lets the image be served with a year-long cache lifetime.
    """

    __tablename__ = "avatar_image"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
