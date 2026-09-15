"""add reporting cycle prevention trigger

Revision ID: d31712335726
Revises: 0fb48f633d33
Create Date: 2026-09-15 16:06:41.339941

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d31712335726"
down_revision: str | Sequence[str] | None = "0fb48f633d33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# See docs/TECHNICAL-DESIGN.md §5.2 for why this can't be an application-level
# check alone: two concurrent reassignments can each pass a pre-write check
# against a snapshot that predates the other and jointly commit a cycle that
# neither could have created alone. Deferring the trigger to COMMIT re-runs
# the check once every statement in the transaction has been applied.
CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION assert_no_reporting_cycle() RETURNS trigger AS $$
DECLARE
    cursor_id UUID := NEW.manager_id;
    hops      INT  := 0;
BEGIN
    WHILE cursor_id IS NOT NULL LOOP
        IF cursor_id = NEW.id THEN
            RAISE EXCEPTION 'Reporting cycle detected for employee %', NEW.id
                USING ERRCODE = 'check_violation';
        END IF;
        SELECT manager_id INTO cursor_id FROM employee WHERE id = cursor_id;
        hops := hops + 1;
        IF hops > 1000 THEN
            RAISE EXCEPTION 'Reporting chain exceeds maximum supported depth';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER = """
CREATE CONSTRAINT TRIGGER employee_no_cycle
    AFTER INSERT OR UPDATE OF manager_id ON employee
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION assert_no_reporting_cycle();
"""

DROP_TRIGGER = "DROP TRIGGER IF EXISTS employee_no_cycle ON employee;"
DROP_FUNCTION = "DROP FUNCTION IF EXISTS assert_no_reporting_cycle();"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(CREATE_FUNCTION)
    op.execute(CREATE_TRIGGER)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(DROP_TRIGGER)
    op.execute(DROP_FUNCTION)
