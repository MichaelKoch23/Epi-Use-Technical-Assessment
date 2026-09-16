"""add audit_log indexes for the change-history feeds

Revision ID: a1c4e7b2f9d0
Revises: d31712335726
Create Date: 2026-09-16

Both audit reads - `GET /employees/{id}/audit` and the global feed at
`GET /audit` - order by `occurred_at DESC, id DESC` and slice with
LIMIT/OFFSET. With no index on either column, Postgres had to sequentially
scan `audit_log` and sort the whole table to return twenty rows; the table
grows by one row per write forever, so this is the one query in the system
whose cost increases without bound while nothing else about the deployment
changes.

The column order matches the ORDER BY exactly (including `DESC`), so the
index can be walked in order and the sort dropped entirely.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c4e7b2f9d0"
down_revision: str | Sequence[str] | None = "d31712335726"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # The global feed: newest first across every employee.
    op.create_index(
        "ix_audit_log_occurred_at",
        "audit_log",
        [sa.text("occurred_at DESC"), sa.text("id DESC")],
    )
    # The per-employee timeline: the same order, within one employee.
    op.create_index(
        "ix_audit_log_employee_occurred_at",
        "audit_log",
        [sa.text("employee_id"), sa.text("occurred_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_audit_log_employee_occurred_at", table_name="audit_log")
    op.drop_index("ix_audit_log_occurred_at", table_name="audit_log")
