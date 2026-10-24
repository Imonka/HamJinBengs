"""Leave, cover cases, cover offers, notifications and the activity log."""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .people import Employee
from .roster import Shift

LEAVE_STATUSES = ("pending", "approved", "rejected")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    leave_type: Mapped[str] = mapped_column(String(60))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual | import | orbyte
    external_ref: Mapped[str | None] = mapped_column(String(120), unique=True)  # Orbyte leave id
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    employee: Mapped[Employee] = relationship(lazy="joined")


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


class Notification(Base):
    """One message to one person. Shown in-app; the email copy waits in the outbox
    (email_status="queued") until an email provider is connected."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    recipient_name: Mapped[str] = mapped_column(String(120))
    recipient_email: Mapped[str] = mapped_column(String(200))
    audience: Mapped[str] = mapped_column(String(16))  # offered | replacement | original | team | manager
    kind: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    email_status: Mapped[str] = mapped_column(String(16), default="queued")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("coverage_cases.id", ondelete="SET NULL"))
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("cover_offers.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
