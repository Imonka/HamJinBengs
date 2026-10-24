"""Writing messages to people.

Every message is stored once per person: they see it in the app (inbox), and an email copy
waits in the outbox with email_status="queued". To actually send email later, add a sender
that picks up queued rows and marks them "sent" -- nothing else needs to change.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.timeutil import now_utc
from app.modules.notifications import schemas
from app.modules.notifications.models import Notification
from app.modules.people.models import Employee


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


# ------------------------------------------------------------------ reading
def notification_out(n: Notification) -> schemas.Notification:
    return schemas.Notification(
        id=n.id,
        recipient_employee_id=n.recipient_employee_id,
        recipient_name=n.recipient_name,
        recipient_email=n.recipient_email,
        audience=n.audience,  # type: ignore[arg-type]
        kind=n.kind,
        subject=n.subject,
        body=n.body,
        email_status=n.email_status,  # type: ignore[arg-type]
        read_at=n.read_at,
        case_id=n.case_id,
        offer_id=n.offer_id,
        created_at=n.created_at,
    )


def outbox(db: Session, limit: int = 300) -> list[schemas.Notification]:
    """Everything sent, newest first (manager view)."""
    rows = db.scalars(select(Notification).order_by(Notification.created_at.desc(), Notification.id.desc())
                      .limit(limit))
    return [notification_out(n) for n in rows]


def inbox(db: Session, employee_id: int, limit: int = 100) -> list[schemas.Notification]:
    rows = db.scalars(select(Notification).where(Notification.recipient_employee_id == employee_id)
                      .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit))
    return [notification_out(n) for n in rows]


def mark_all_read(db: Session, employee_id: int) -> None:
    db.execute(update(Notification).where(Notification.recipient_employee_id == employee_id,
                                          Notification.read_at.is_(None)).values(read_at=now_utc()))
    db.commit()
