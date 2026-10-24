"""Writing messages to people.

Every message is stored once per person: they see it in the app (inbox), and an email copy
waits in the outbox with email_status="queued". To actually send email later, add a sender
that picks up queued rows and marks them "sent" -- nothing else needs to change.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Employee, Notification


def managers(db: Session) -> list[Employee]:
    return list(
        db.scalars(select(Employee).where(Employee.access == "manager", Employee.active.is_(True)))
    )


def notify(
    db: Session,
    recipient: Employee,
    *,
    audience: str,
    kind: str,
    subject: str,
    body: str,
    case_id: int | None = None,
    offer_id: int | None = None,
) -> Notification:
    n = Notification(
        recipient_employee_id=recipient.id,
        recipient_name=recipient.name,
        recipient_email=recipient.email,
        audience=audience,
        kind=kind,
        subject=subject,
        body=body,
        email_status="queued",
        case_id=case_id,
        offer_id=offer_id,
    )
    db.add(n)
    return n


def notify_managers(db: Session, *, kind: str, subject: str, body: str, case_id: int | None = None,
                    offer_id: int | None = None, exclude_id: int | None = None) -> None:
    for m in managers(db):
        if m.id != exclude_id:
            notify(db, m, audience="manager", kind=kind, subject=subject, body=body,
                   case_id=case_id, offer_id=offer_id)
