"""People: job roles and employees. Employees are also the app's users.

This is the data Orbyte will own once it is connected (see people/sources.py)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


ACCESS_LEVELS = ("manager", "staff")


class Role(Base):
    """A job role such as Cashier, Server or Chef. Managed by the manager."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#0f766e")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Employee(Base):
    """Everyone who uses the app. access="manager" can run everything;
    access="staff" can only see their own shifts and accept/decline cover offers."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    access: Mapped[str] = mapped_column(String(16), default="staff")
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Personal weekly limit (e.g. a part-timer). None = the branch rule applies.
    max_hours_per_week: Mapped[float | None] = mapped_column(Float)
    orbyte_id: Mapped[str | None] = mapped_column(String(80), unique=True)

    pin_hash: Mapped[str] = mapped_column(Text)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    role: Mapped[Role | None] = relationship(lazy="joined")

    @property
    def is_manager(self) -> bool:
        return self.access == "manager"
