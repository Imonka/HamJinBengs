"""The scheduling model: branch rules, shift patterns (demand) and shifts (the roster)."""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .people import Employee, Role

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]  # 0 = Monday ... 6 = Sunday


class BranchSettings(Base):
    """One row (id = 1). Every working-time rule is a column here so the manager can change it."""

    __tablename__ = "branch_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    branch_name: Mapped[str] = mapped_column(String(120), default="My Branch")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kuala_Lumpur")
    open_time: Mapped[time] = mapped_column(Time, default=time(7, 0))
    close_time: Mapped[time] = mapped_column(Time, default=time(22, 0))
    max_hours_per_day: Mapped[float] = mapped_column(Float, default=8)
    max_hours_per_week: Mapped[float] = mapped_column(Float, default=40)
    max_days_per_week: Mapped[int] = mapped_column(Integer, default=6)
    min_rest_hours: Mapped[float] = mapped_column(Float, default=10)
    operating_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=lambda: list(ALL_DAYS))
    week_starts_on: Mapped[int] = mapped_column(Integer, default=0)
    leave_source: Mapped[str] = mapped_column(String(16), default="manual")
    orbyte_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShiftPattern(Base):
    """A repeating shift, e.g. "Weekday morning 07:00-15:00, Mon-Fri",
    with how many people of each role it needs (requirements)."""

    __tablename__ = "shift_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    days: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    requirements: Mapped[list["PatternRequirement"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan", lazy="selectin"
    )


class PatternRequirement(Base):
    __tablename__ = "pattern_requirements"
    __table_args__ = (UniqueConstraint("pattern_id", "role_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("shift_patterns.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    headcount: Mapped[int] = mapped_column(Integer)

    pattern: Mapped[ShiftPattern] = relationship(back_populates="requirements")
    role: Mapped[Role] = relationship(lazy="joined")


SHIFT_STATUSES = ("scheduled", "needs_cover", "covered", "cancelled")
SHIFT_SOURCES = ("generated", "manual", "cover")


class Shift(Base):
    """One person working one block of time.

    status: scheduled   - they are working it (counts towards their hours)
            needs_cover - they are on leave and nobody has taken it yet
            covered     - they are on leave and someone else took it (see the replacement shift)
            cancelled
    source: generated (by the roster generator), manual (added by the manager),
            cover (created when someone accepted a cover offer)
    """

    __tablename__ = "shifts"
    __table_args__ = (Index("shifts_employee_date_idx", "employee_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    pattern_id: Mapped[int | None] = mapped_column(ForeignKey("shift_patterns.id", ondelete="SET NULL"))
    date: Mapped[date] = mapped_column(Date, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee | None] = relationship(lazy="joined")
    role: Mapped[Role] = relationship(lazy="joined")
    pattern: Mapped[ShiftPattern | None] = relationship(lazy="joined")
