"""The activity log: one line per notable change, shown on the manager's Desk.
Any module may write to it; only the dashboard module reads it."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def log(db: Session, kind: str, message: str) -> None:
    """Add a line to the activity feed. Committed together with the caller's changes."""
    db.add(Activity(kind=kind, message=message))
