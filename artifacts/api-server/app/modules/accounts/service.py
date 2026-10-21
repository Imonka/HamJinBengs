"""Sign-in with email + PIN, and bearer-token sessions.

* PINs are 4-8 digits, stored only as a salted scrypt hash.
* After 5 wrong PINs the account is locked for 15 minutes (PINs are short, so this matters).
* A successful sign-in returns a random token; only its SHA-256 is stored.
"""

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import activity
from app.core.config import config
from app.core.errors import BadRequest, Conflict, TooManyAttempts, Unauthorized
from app.core.timeutil import now_utc
from app.modules.accounts import schemas
from app.modules.accounts.models import AuthSession
from app.modules.people.models import Employee

_PIN_RE = re.compile(r"^\d{4,8}$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def validate_pin(pin: str) -> str:
    if not _PIN_RE.match(pin or ""):
        raise BadRequest("PIN must be 4 to 8 digits.")
    return pin


def hash_pin(pin: str) -> str:
    validate_pin(pin)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(db: Session, email: str, pin: str) -> tuple[str, Employee]:
    user = db.scalar(select(Employee).where(Employee.email == email.strip().lower()))
    now = now_utc()
    if user is None or not user.active:
        raise Unauthorized("Email or PIN is incorrect.")
    if user.locked_until and user.locked_until > now:
        minutes = max(1, round((user.locked_until - now).total_seconds() / 60))
        raise TooManyAttempts(f"Too many wrong PINs. Try again in {minutes} minute(s).")
    if not verify_pin(pin, user.pin_hash):
        user.failed_logins += 1
        if user.failed_logins >= config.max_failed_logins:
            user.locked_until = now + timedelta(minutes=config.lockout_minutes)
            user.failed_logins = 0
        db.commit()
        raise Unauthorized("Email or PIN is incorrect.")

    user.failed_logins = 0
    user.locked_until = None
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=_token_hash(token),
            employee_id=user.id,
            expires_at=now + timedelta(days=config.session_days),
        )
    )
    db.commit()
    return token, user


def user_for_token(db: Session, token: str) -> Employee | None:
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    if session is None or session.expires_at <= now_utc() or not session.employee.active:
        return None
    return session.employee


def logout(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    db.commit()


def end_all_sessions(db: Session, employee_id: int) -> None:
    db.execute(delete(AuthSession).where(AuthSession.employee_id == employee_id))


def change_pin(db: Session, user: Employee, current_pin: str, new_pin: str) -> None:
    if not verify_pin(current_pin, user.pin_hash):
        raise BadRequest("Current PIN is incorrect.")
    user.pin_hash = hash_pin(new_pin)
    db.commit()


# ------------------------------------------------------------------ self-service
def update_profile(db: Session, user: Employee, data: schemas.ProfileInput) -> Employee:
    """The signed-in person editing their own name, email and phone."""
    from app.modules.people.service import clean_email

    if not data.name.strip():
        raise BadRequest("Name is required.")
    email = clean_email(db, data.email, user.id)
    if email != user.email and not (data.current_pin and verify_pin(data.current_pin, user.pin_hash)):
        raise BadRequest("Enter your current PIN to change your email.")
    user.name = data.name.strip()
    user.email = email
    user.phone = (data.phone or "").strip() or None
    activity.log(db, "profile_updated", f"{user.name} updated their own details")
    db.commit()
    db.refresh(user)
    return user


# ------------------------------------------------------------------ server-only (CLI) actions
def set_access(db: Session, email: str, access: str) -> Employee:
    """Grant or remove manager access. Deliberately not exposed in the web app."""
    from app.modules.people.service import active_manager_count, find_by_email

    if access not in ("manager", "staff"):
        raise BadRequest('Access must be "manager" or "staff".')
    e = find_by_email(db, email)
    if e.access == access:
        return e
    if e.access == "manager" and e.active and active_manager_count(db) <= 1:
        raise Conflict("This is the only manager. Make someone else a manager first.")
    e.access = access
    end_all_sessions(db, e.id)  # their screens change, so make them sign in again
    activity.log(db, "access_changed", f"{e.name} is now {access}")
    db.commit()
    return e


def reset_pin(db: Session, email: str, pin: str) -> Employee:
    """Recovery for a forgotten PIN. Deliberately not exposed in the web app."""
    from app.modules.people.service import find_by_email

    e = find_by_email(db, email)
    e.pin_hash = hash_pin(pin)
    e.failed_logins, e.locked_until = 0, None
    end_all_sessions(db, e.id)
    activity.log(db, "pin_reset", f"PIN reset for {e.name} from the server")
    db.commit()
    return e
