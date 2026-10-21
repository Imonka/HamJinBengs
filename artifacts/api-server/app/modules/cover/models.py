"""Cover cases (a shift left empty by approved leave) and the offers sent to fill them."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.leave.models import LeaveRequest
from app.modules.people.models import Employee
from app.modules.scheduling.models import Shift


COVERAGE_STATUSES = ("open", "offered", "filled", "cancelled")


class CoverageCase(Base):
    """A shift that needs a replacement because its owner is on approved leave."""

    __tablename__ = "coverage_cases"
    __table_args__ = (UniqueConstraint("shift_id", "leave_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    leave_id: Mapped[int] = mapped_column(ForeignKey("leave_requests.id", ondelete="CASCADE"))
    original_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="open")
    replacement_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    replacement_shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id", ondelete="SET NULL"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shift: Mapped[Shift] = relationship(foreign_keys=[shift_id], lazy="joined")
    leave: Mapped[LeaveRequest] = relationship(lazy="joined")
    original_employee: Mapped[Employee] = relationship(foreign_keys=[original_employee_id], lazy="joined")
    replacement_employee: Mapped[Employee | None] = relationship(
        foreign_keys=[replacement_employee_id], lazy="joined"
    )
    offers: Mapped[list["CoverOffer"]] = relationship(
        back_populates="case", lazy="selectin", order_by="CoverOffer.id"
    )


OFFER_STATUSES = ("pending", "accepted", "declined", "withdrawn", "expired")


class CoverOffer(Base):
    """The manager asking one person to take a cover shift. Several people can be asked
    at once; the first to accept gets it and everyone else's offer expires."""

    __tablename__ = "cover_offers"
    __table_args__ = (
        # A person can only have one live offer per case.
        Index(
            "cover_offers_one_pending_idx",
            "case_id",
            "employee_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("coverage_cases.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    message: Mapped[str | None] = mapped_column(Text)
    response_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped[CoverageCase] = relationship(back_populates="offers")
    employee: Mapped[Employee] = relationship(lazy="joined")
