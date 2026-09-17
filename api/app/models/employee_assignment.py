import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeAssignment(Base):
    """A date-bounded reporting edge.

    This table is authoritative for reporting history; ``Employee.manager_id`` is
    a cache of whichever row is effective today, kept in step by the
    ``sync_effective_assignments()`` database function. ``valid_to`` is half-open:
    it is the first day the assignment is no longer in force, so ``valid_to`` of
    one run may equal ``valid_from`` of the next.
    """

    __tablename__ = "employee_assignment"
    __table_args__ = (
        CheckConstraint(
            "manager_id IS DISTINCT FROM employee_id", name="assignment_not_self"
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="assignment_range_ok"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employee.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="SET NULL")
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
