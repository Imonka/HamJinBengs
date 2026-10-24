"""/settings, /shift-patterns, /shifts, /roster and /me/shifts: the scheduling system."""

from datetime import date

from fastapi import APIRouter, Query, Response

from app.core.db import DB
from app.modules.accounts.deps import Manager, User
from app.modules.scheduling import patterns, roster, rules, schemas, shifts

router = APIRouter()


# ---------------------------------------------------------------- branch rules
@router.get("/settings", response_model=schemas.Settings, tags=["settings"])
def get_settings(db: DB, _: User):
    return rules.settings_out(rules.get_settings(db))


@router.put("/settings", response_model=schemas.Settings, tags=["settings"])
def update_settings(data: schemas.SettingsInput, db: DB, _: Manager):
    return rules.settings_out(rules.update_settings(db, data))


# ---------------------------------------------------------------- shift patterns
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


# ---------------------------------------------------------------- shifts
@router.get("/shifts", response_model=list[schemas.Shift], tags=["shifts"])
def list_shifts(db: DB, _: Manager, date_from: date | None = Query(None, alias="from"),
                date_to: date | None = Query(None, alias="to"), employeeId: int | None = None,  # noqa: N803
                roleId: int | None = None, status: schemas.ShiftStatus | None = None):  # noqa: N803
    return shifts.list_shifts(db, date_from, date_to, employeeId, roleId, status)


@router.post("/shifts", response_model=schemas.Shift, status_code=201, tags=["shifts"])
def create_shift(data: schemas.ShiftInput, db: DB, _: Manager):
    return shifts.create_shift(db, data)


@router.put("/shifts/{shiftId}", response_model=schemas.Shift, tags=["shifts"])
def update_shift(shiftId: int, data: schemas.ShiftInput, db: DB, _: Manager):  # noqa: N803
    return shifts.update_shift(db, shiftId, data)


@router.delete("/shifts/{shiftId}", status_code=204, tags=["shifts"])
def delete_shift(shiftId: int, db: DB, _: Manager):  # noqa: N803
    shifts.delete_shift(db, shiftId)
    return Response(status_code=204)


@router.get("/me/shifts", response_model=list[schemas.Shift], tags=["me"])
def my_shifts(db: DB, user: User, date_from: date | None = Query(None, alias="from"),
              date_to: date | None = Query(None, alias="to")):
    return shifts.my_shifts(db, user.id, date_from, date_to)


# ---------------------------------------------------------------- roster
@router.get("/roster/week", response_model=schemas.RosterWeek, tags=["roster"])
def roster_week(db: DB, _: Manager, start: date):
    return roster.week_view(db, start)


@router.post("/roster/generate", response_model=schemas.GenerateRosterResult, tags=["roster"])
def generate_roster(data: schemas.GenerateRosterInput, db: DB, _: Manager):
    return roster.generate(db, data.week_start, data.replace_existing)
