from sqlalchemy.orm import Session

from ..models import Activity


def log(db: Session, kind: str, message: str) -> None:
    """Add a line to the activity feed. Committed together with the caller's changes."""
    db.add(Activity(kind=kind, message=message))
