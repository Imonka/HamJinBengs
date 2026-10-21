"""Demo data for "Kopi Lane — Mid Valley". Dates are relative to today, so the demo always looks live.

Manager: farah@kopilane.my / PIN 1234. Everyone else: <firstname>@kopilane.my / PIN 1111.
"""

from datetime import time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import schemas
from .db import Base, engine
from .models import BranchSettings, CoverageCase, Employee, PatternRequirement, Role, Shift, ShiftPattern
from .services import coverage, leave, roster
from .services.employees import add_employee
from .services.settings import get_rules
from .timeutil import local_today, now_utc

ROLES = [("Cashier", "#b45309"), ("Server", "#0f766e"), ("Chef", "#7c3aed")]

# (name, email, role, personal weekly limit)
STAFF = [
    ("Aisyah Rahman", "aisyah", "Cashier", None),
    ("Daniel Tan", "daniel", "Cashier", None),
    ("Kavitha Nair", "kavitha", "Cashier", None),
    ("Hafiz Ismail", "hafiz", "Cashier", None),
    ("Mei Ling Wong", "meiling", "Server", 24),
    ("Arjun Pillai", "arjun", "Server", None),
    ("Nurul Huda", "nurul", "Server", None),
    ("Jason Lim", "jason", "Server", None),
    ("Siti Aminah", "siti", "Server", None),
    ("Ravi Kumar", "ravi", "Server", None),
    ("Chloe Ng", "chloe", "Server", None),
    ("Amirul Hakim", "amirul", "Server", None),
    ("Ahmad Faizal", "ahmad", "Chef", None),
    ("Wei Jie Chong", "weijie", "Chef", None),
    ("Priya Devi", "priya", "Chef", None),
    ("Zulkarnain Osman", "zul", "Chef", None),
    ("Hui Min Lee", "huimin", "Chef", None),
    ("Farid Yusof", "farid", "Chef", None),
    ("Suresh Raj", "suresh", "Chef", None),
    ("Grace Lim", "grace", "Chef", None),
]

WEEKDAYS, WEEKEND = [0, 1, 2, 3, 4], [5, 6]
# (pattern name, start, end, days, {role: headcount})
PATTERNS = [
    ("Weekday morning", time(7), time(15), WEEKDAYS, {"Cashier": 1, "Server": 2, "Chef": 2}),
    ("Weekday evening", time(14), time(22), WEEKDAYS, {"Cashier": 1, "Server": 2, "Chef": 2}),
    ("Weekend morning", time(7), time(15), WEEKEND, {"Cashier": 1, "Server": 3, "Chef": 3}),
    ("Weekend evening", time(14), time(22), WEEKEND, {"Cashier": 1, "Server": 3, "Chef": 3}),
]


def reset_database() -> None:
    from . import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _future_shifts(db: Session, employee: Employee, limit: int = 3) -> list[Shift]:
    return list(db.scalars(
        select(Shift).where(Shift.employee_id == employee.id, Shift.status == "scheduled",
                            Shift.starts_at > now_utc() + timedelta(hours=3))
        .order_by(Shift.starts_at).limit(limit)
    ))


def _leave_for(db: Session, who: Employee, shift: Shift, kind: str, reason: str, days: int = 1,
               status: str = "approved") -> list[CoverageCase]:
    result = leave.create_leave(db, schemas.LeaveInput(
        employee_id=who.id, leave_type=kind, start_date=shift.date,
        end_date=shift.date + timedelta(days=days - 1), status=status, reason=reason))
    return [db.get(CoverageCase, c.id) for c in result.coverage_cases]


def _offer(db: Session, case: CoverageCase, manager: Employee, n: int, prefer: Employee | None = None,
           message: str | None = None) -> list[Employee]:
    eligible = [c.employee.id for c in coverage.candidates(db, case.id).eligible]
    if prefer is not None and prefer.id in eligible:
        eligible.remove(prefer.id)
        eligible.insert(0, prefer.id)
    chosen = eligible[:n]
    if chosen:
        coverage.send_offers(db, case.id, schemas.SendOffersInput(employee_ids=chosen, message=message), manager)
    return [db.get(Employee, i) for i in chosen]


def _pending_offer_id(db: Session, case: CoverageCase, who: Employee) -> int:
    db.refresh(case)
    return next(o.id for o in case.offers if o.employee_id == who.id and o.status == "pending")


def seed(db: Session) -> None:
    db.add(BranchSettings(
        id=1, branch_name="Kopi Lane — Mid Valley", timezone="Asia/Kuala_Lumpur",
        open_time=time(7), close_time=time(22), max_hours_per_day=8, max_hours_per_week=40,
        max_days_per_week=6, min_rest_hours=10, operating_days=list(range(7)), week_starts_on=0,
        leave_source="import",
    ))
    roles = {name: Role(name=name, color=color) for name, color in ROLES}
    db.add_all(roles.values())
    db.flush()
    for name, start, end, days, needs in PATTERNS:
        db.add(ShiftPattern(name=name, start_time=start, end_time=end, days=days, active=True, requirements=[
            PatternRequirement(role_id=roles[r].id, headcount=n) for r, n in needs.items()]))
    db.commit()

    manager = add_employee(db, name="Farah Zulkifli", email="farah@kopilane.my", pin="1234", access="manager",
                           phone="+60 12-345 6789")
    people = {}
    for name, user, role, limit in STAFF:
        people[user] = add_employee(db, name=name, email=f"{user}@kopilane.my", pin="1111", role_name=role,
                                    max_hours_per_week=limit, orbyte_id=f"KL-{len(people) + 101:04d}")

    # Roster: this week (including days already past, for history) and next week.
    rules = get_rules(db)
    today = local_today(rules.tz)
    roster.generate(db, today, replace_existing=False, include_past=True)
    roster.generate(db, today + timedelta(days=7), replace_existing=False)

    # 1) Arjun (Server) on annual leave for two days -> two cover cases.
    arjun_shifts = _future_shifts(db, people["arjun"], 2)
    span = (arjun_shifts[-1].date - arjun_shifts[0].date).days + 1
    cases = _leave_for(db, people["arjun"], arjun_shifts[0], "Annual", "Family wedding in Ipoh", days=span)
    if cases:
        # Case 1: two people asked, the first accepts (the other offer expires).
        asked = _offer(db, cases[0], manager, 2, message="Can anyone help? Thank you!")
        if asked:
            coverage.accept_offer(db, _pending_offer_id(db, cases[0], asked[0]), asked[0])
    if len(cases) > 1:
        # Case 2: one person asked and declined -> back to open.
        asked = _offer(db, cases[1], manager, 1)
        if asked:
            coverage.decline_offer(db, _pending_offer_id(db, cases[1], asked[0]), asked[0],
                                   "Sorry, I have class that day.")

    # 2) Daniel (Cashier) on medical leave -> Aisyah and one more cashier have a pending offer.
    daniel_shifts = _future_shifts(db, people["daniel"], 1)
    if daniel_shifts:
        cases = _leave_for(db, people["daniel"], daniel_shifts[0], "Medical", "Clinic appointment")
        if cases:
            _offer(db, cases[0], manager, 2, prefer=people["aisyah"])

    # 3) Ahmad (Chef) on emergency leave next week -> open, nobody asked yet.
    ahmad_next = [s for s in _future_shifts(db, people["ahmad"], 8) if s.date >= today + timedelta(days=4)]
    if ahmad_next:
        _leave_for(db, people["ahmad"], ahmad_next[0], "Emergency", "Family matter")

    # 4) Jason (Server) has asked for leave next week; waiting for the manager.
    jason_next = [s for s in _future_shifts(db, people["jason"], 8) if s.date >= today + timedelta(days=5)]
    if jason_next:
        _leave_for(db, people["jason"], jason_next[0], "Annual", "Trip to Penang", status="pending")
