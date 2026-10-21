"""Messages to people (in-app inbox plus a queued email copy in the outbox)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


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
