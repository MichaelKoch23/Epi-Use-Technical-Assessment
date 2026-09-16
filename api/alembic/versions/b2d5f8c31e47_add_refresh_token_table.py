"""add refresh_token table for revocable sessions

Revision ID: b2d5f8c31e47
Revises: a1c4e7b2f9d0
Create Date: 2026-09-16

Refresh tokens previously carried a seven-day lifetime with no server-side
state behind them, which meant three things the API nonetheless implied it
offered: logging out did not end the session (it only cleared the browser's
copy), a captured token stayed usable for its full lifetime, and "rotation"
issued a new token without the old one ever ceasing to work.

This table is the server-side half that makes those operations real. It
stores the `jti` of each issued token - never the token itself, since the
JWT signature already proves provenance and the row only has to answer
whether that specific token is still live.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d5f8c31e47"
down_revision: str | Sequence[str] | None = "a1c4e7b2f9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "refresh_token",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_user.id"],
            name=op.f("fk_refresh_token_user_id_app_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_token")),
    )
    # "Revoke every live token for this user" (on detected replay, or a
    # sign-out-everywhere) is the one query that is not a primary-key lookup.
    op.create_index(
        "ix_refresh_token_user_live",
        "refresh_token",
        ["user_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_refresh_token_user_live", table_name="refresh_token")
    op.drop_table("refresh_token")
