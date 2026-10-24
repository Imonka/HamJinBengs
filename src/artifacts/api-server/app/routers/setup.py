"""Manager setup: branch rules, job roles and shift patterns."""

from fastapi import APIRouter, Response

from .. import schemas
from ..deps import DB, Manager, User
from ..services import patterns, roles, settings

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=schemas.Settings)
def get_settings(db: DB, _: User):
    return settings.settings_out(settings.get_settings(db))


@router.put("/settings", response_model=schemas.Settings)
def update_settings(data: schemas.SettingsInput, db: DB, _: Manager):
    return settings.settings_out(settings.update_settings(db, data))


@router.get("/roles", response_model=list[schemas.Role], tags=["roles"])
def list_roles(db: DB, _: User):
    return roles.list_roles(db)


@router.post("/roles", response_model=schemas.Role, status_code=201, tags=["roles"])
def create_role(data: schemas.RoleInput, db: DB, _: Manager):
    return roles.create_role(db, data)


@router.put("/roles/{roleId}", response_model=schemas.Role, tags=["roles"])
def update_role(roleId: int, data: schemas.RoleInput, db: DB, _: Manager):  # noqa: N803
    return roles.update_role(db, roleId, data)


@router.delete("/roles/{roleId}", status_code=204, tags=["roles"])
def delete_role(roleId: int, db: DB, _: Manager):  # noqa: N803
    roles.delete_role(db, roleId)
    return Response(status_code=204)


@router.get("/shift-patterns", response_model=list[schemas.ShiftPattern], tags=["patterns"])
def list_patterns(db: DB, _: Manager):
    return patterns.list_patterns(db)


@router.post("/shift-patterns", response_model=schemas.ShiftPattern, status_code=201, tags=["patterns"])
def create_pattern(data: schemas.ShiftPatternInput, db: DB, _: Manager):
    return patterns.create_pattern(db, data)


@router.put("/shift-patterns/{patternId}", response_model=schemas.ShiftPattern, tags=["patterns"])
def update_pattern(patternId: int, data: schemas.ShiftPatternInput, db: DB, _: Manager):  # noqa: N803
    return patterns.update_pattern(db, patternId, data)


@router.delete("/shift-patterns/{patternId}", status_code=204, tags=["patterns"])
def delete_pattern(patternId: int, db: DB, _: Manager):  # noqa: N803
    patterns.delete_pattern(db, patternId)
    return Response(status_code=204)
