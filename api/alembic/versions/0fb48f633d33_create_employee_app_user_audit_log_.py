from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0fb48f633d33"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "app_user",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_user")),
        sa.UniqueConstraint("email", name=op.f("uq_app_user_email")),
    )
    op.create_table(
        "employee",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("employee_number", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default="ZAR", nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=True),
        sa.Column("avatar_override_url", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["employee.id"],
            name=op.f("fk_employee_manager_id_employee"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee")),
    )
    op.create_table(
        "audit_log",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["app_user.id"], name=op.f("fk_audit_log_actor_id_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_audit_log_employee_id_employee"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )

    op.create_check_constraint(
        "employee_not_own_manager",
        "employee",
        "manager_id IS DISTINCT FROM id",
    )
    op.create_check_constraint(
        "employee_salary_non_negative",
        "employee",
        "salary >= 0",
    )
    op.create_check_constraint(
        "employee_birth_date_sane",
        "employee",
        "birth_date > DATE '1900-01-01'",
    )

    op.create_index(
        "uq_employee_number",
        "employee",
        ["employee_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_employee_email",
        "employee",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_employee_manager",
        "employee",
        ["manager_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_employee_name_trgm",
        "employee",
        [sa.text("(first_name || ' ' || last_name) gin_trgm_ops")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_employee_name_trgm", table_name="employee")
    op.drop_index("ix_employee_manager", table_name="employee")
    op.drop_index("uq_employee_email", table_name="employee")
    op.drop_index("uq_employee_number", table_name="employee")

    op.drop_constraint("employee_birth_date_sane", "employee", type_="check")
    op.drop_constraint("employee_salary_non_negative", "employee", type_="check")
    op.drop_constraint("employee_not_own_manager", "employee", type_="check")

    op.drop_table("audit_log")
    op.drop_table("employee")
    op.drop_table("app_user")
