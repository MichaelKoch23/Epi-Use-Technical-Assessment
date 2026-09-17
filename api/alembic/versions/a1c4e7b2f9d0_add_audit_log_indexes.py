from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e7b2f9d0"
down_revision: str | Sequence[str] | None = "d31712335726"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_log_occurred_at",
        "audit_log",
        [sa.text("occurred_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_audit_log_employee_occurred_at",
        "audit_log",
        [sa.text("employee_id"), sa.text("occurred_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_employee_occurred_at", table_name="audit_log")
    op.drop_index("ix_audit_log_occurred_at", table_name="audit_log")
