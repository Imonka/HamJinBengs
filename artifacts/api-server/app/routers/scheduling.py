"""Shifts and the weekly roster (manager only)."""

from datetime import date

from fastapi import APIRouter, Query, Response

from .. import schemas
from ..deps import DB, Manager
from ..services import roster, shifts

router = APIRouter()


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


@router.get("/roster/week", response_model=schemas.RosterWeek, tags=["roster"])
def roster_week(db: DB, _: Manager, start: date):
    return roster.week_view(db, start)


@router.post("/roster/generate", response_model=schemas.GenerateRosterResult, tags=["roster"])
def generate_roster(data: schemas.GenerateRosterInput, db: DB, _: Manager):
    return roster.generate(db, data.week_start, data.replace_existing)
