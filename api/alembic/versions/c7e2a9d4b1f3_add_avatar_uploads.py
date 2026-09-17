"""add avatar_image table and app_user.avatar_override_url for photo uploads

Revision ID: c7e2a9d4b1f3
Revises: b2d5f8c31e47
Create Date: 2026-09-17

Uploaded profile pictures are stored in the database itself: the Cloud Run
container has no durable filesystem, and the brief requires every change
to be committed to the remote database. `employee.avatar_override_url`
already exists and simply points at `/api/v1/avatars/<id>` for an upload;
accounts gain the same column so the profile page can carry a photo too.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e2a9d4b1f3"
down_revision: str | Sequence[str] | None = "b2d5f8c31e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "avatar_image",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_avatar_image")),
    )
    op.add_column("app_user", sa.Column("avatar_override_url", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("app_user", "avatar_override_url")
    op.drop_table("avatar_image")
