from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7e2a9d4b1f3"
down_revision: str | Sequence[str] | None = "b2d5f8c31e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
    op.add_column(
        "app_user", sa.Column("avatar_override_url", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("app_user", "avatar_override_url")
    op.drop_table("avatar_image")
