from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3b91c5ad284"
down_revision: str | Sequence[str] | None = "c7e2a9d4b1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_NO_OVERLAP = """
ALTER TABLE employee_assignment
  ADD CONSTRAINT assignment_no_overlap
  EXCLUDE USING gist (
      employee_id WITH =,
      daterange(valid_from, valid_to, '[)') WITH &&
  );
"""

DROP_NO_OVERLAP = """
ALTER TABLE employee_assignment DROP CONSTRAINT IF EXISTS assignment_no_overlap;
"""

BACKFILL = """
INSERT INTO employee_assignment (id, employee_id, manager_id, valid_from, valid_to, reason)
SELECT gen_random_uuid(), e.id, e.manager_id, DATE '2020-01-01', NULL, 'Initial load'
FROM employee e
WHERE e.deleted_at IS NULL;
"""

CREATE_SYNC_FUNCTION = """
CREATE OR REPLACE FUNCTION sync_effective_assignments() RETURNS integer AS $$
DECLARE
    touched integer;
BEGIN
    WITH effective AS (
        SELECT a.employee_id, a.manager_id
        FROM employee_assignment a
        WHERE a.valid_from <= CURRENT_DATE
          AND (a.valid_to IS NULL OR a.valid_to > CURRENT_DATE)
    )
    UPDATE employee e
       SET manager_id = ef.manager_id,
           version    = e.version + 1,
           updated_at = now()
      FROM effective ef
     WHERE e.id = ef.employee_id
       AND e.deleted_at IS NULL
       AND e.manager_id IS DISTINCT FROM ef.manager_id;

    GET DIAGNOSTICS touched = ROW_COUNT;
    RETURN touched;
END;
$$ LANGUAGE plpgsql;
"""

DROP_SYNC_FUNCTION = "DROP FUNCTION IF EXISTS sync_effective_assignments();"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "employee_assignment",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_employee_assignment_employee_id_employee"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["employee.id"],
            name=op.f("fk_employee_assignment_manager_id_employee"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["app_user.id"],
            name=op.f("fk_employee_assignment_created_by_app_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_assignment")),
    )

    op.create_check_constraint(
        "assignment_not_self",
        "employee_assignment",
        "manager_id IS DISTINCT FROM employee_id",
    )
    op.create_check_constraint(
        "assignment_range_ok",
        "employee_assignment",
        "valid_to IS NULL OR valid_to > valid_from",
    )

    op.execute(CREATE_NO_OVERLAP)

    op.create_index(
        "ix_assignment_employee_from",
        "employee_assignment",
        ["employee_id", sa.text("valid_from DESC")],
    )
    op.create_index(
        "ix_assignment_manager",
        "employee_assignment",
        ["manager_id"],
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    op.create_index(
        "ix_assignment_range",
        "employee_assignment",
        [sa.text("daterange(valid_from, valid_to, '[)')")],
        postgresql_using="gist",
    )

    op.execute(BACKFILL)
    op.execute(CREATE_SYNC_FUNCTION)


def downgrade() -> None:
    op.execute(DROP_SYNC_FUNCTION)
    op.drop_index("ix_assignment_range", table_name="employee_assignment")
    op.drop_index("ix_assignment_manager", table_name="employee_assignment")
    op.drop_index("ix_assignment_employee_from", table_name="employee_assignment")
    op.execute(DROP_NO_OVERLAP)
    op.drop_table("employee_assignment")
