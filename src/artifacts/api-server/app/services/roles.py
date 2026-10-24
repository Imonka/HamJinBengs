"""Job roles (Cashier, Server, Chef, ...). The manager can add, rename and remove them."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..errors import BadRequest, Conflict, NotFound
from ..models import Employee, PatternRequirement, Role, Shift
from . import activity

PALETTE = ["#0f766e", "#b45309", "#7c3aed", "#be123c", "#1d4ed8", "#4d7c0f", "#a21caf", "#0e7490"]


def _counts(db: Session) -> dict[int, int]:
    return dict(
        db.execute(
            select(Employee.role_id, func.count())
            .where(Employee.active.is_(True), Employee.role_id.is_not(None))
            .group_by(Employee.role_id)
        ).all()
    )


def role_out(r: Role, count: int) -> schemas.Role:
    return schemas.Role(id=r.id, name=r.name, color=r.color, employee_count=count)


def list_roles(db: Session) -> list[schemas.Role]:
    counts = _counts(db)
    return [role_out(r, counts.get(r.id, 0)) for r in db.scalars(select(Role).order_by(Role.name))]


def find_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(func.lower(Role.name) == name.strip().lower()))


def _validate(db: Session, data: schemas.RoleInput, current_id: int | None = None) -> str:
    name = data.name.strip()
    if not name:
        raise BadRequest("Role name is required.")
    existing = find_role_by_name(db, name)
    if existing is not None and existing.id != current_id:
        raise Conflict(f'A role called "{existing.name}" already exists.')
    return name


def create_role(db: Session, data: schemas.RoleInput) -> schemas.Role:
    name = _validate(db, data)
    count = db.scalar(select(func.count()).select_from(Role)) or 0
    role = Role(name=name, color=data.color or PALETTE[count % len(PALETTE)])
    db.add(role)
    activity.log(db, "role_added", f"Added role {name}")
    db.commit()
    return role_out(role, 0)


def update_role(db: Session, role_id: int, data: schemas.RoleInput) -> schemas.Role:
    role = db.get(Role, role_id)
    if role is None:
        raise NotFound("Role not found.")
    role.name = _validate(db, data, role_id)
    if data.color:
        role.color = data.color
    db.commit()
    return role_out(role, _counts(db).get(role.id, 0))


def delete_role(db: Session, role_id: int) -> None:
    role = db.get(Role, role_id)
    if role is None:
        raise NotFound("Role not found.")
    people = db.scalar(select(func.count()).select_from(Employee).where(Employee.role_id == role_id)) or 0
    patterns = db.scalar(
        select(func.count()).select_from(PatternRequirement).where(PatternRequirement.role_id == role_id)
    ) or 0
    shifts = db.scalar(select(func.count()).select_from(Shift).where(Shift.role_id == role_id)) or 0
    if people or patterns or shifts:
        used = [f"{n} {what}" for n, what in ((people, "employee(s)"), (patterns, "shift pattern(s)"),
                                               (shifts, "shift(s)")) if n]
        raise Conflict(f"{role.name} is still used by {', '.join(used)}. Move or remove those first.")
    db.delete(role)
    activity.log(db, "role_removed", f"Removed role {role.name}")
    db.commit()
