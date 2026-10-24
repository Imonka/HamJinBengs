"""Tests for the scheduling engine (no database needed)."""

from datetime import date, datetime, time, timedelta

from app.modules.scheduling.engine import (
    Booking,
    CheckContext,
    LeaveBlock,
    PatternDemand,
    ProposedShift,
    Rules,
    StaffMember,
    evaluate,
    generate_week,
    rank_candidates,
)
from app.modules.scheduling.engine.constraints import COVER
from app.core.timeutil import at

RULES = Rules()
TZ = RULES.tz
MONDAY = date(2030, 1, 7)  # a Monday well in the future
NOW = datetime(2030, 1, 1, 9, 0, tzinfo=TZ)
CASHIER, SERVER, CHEF = 1, 2, 3


def shift(day: date, start: int, end: int, role: int = SERVER) -> ProposedShift:
    return ProposedShift(day, at(day, time(start), TZ), at(day, time(end), TZ), role, "Server")


def booking(day: date, start: int, end: int, role: int = SERVER) -> Booking:
    return Booking(day, at(day, time(start), TZ), at(day, time(end), TZ), role)


def person(pid: int, role: int = SERVER, **kw) -> StaffMember:
    return StaffMember(id=pid, name=f"P{pid}", role_id=role, role_name="Server", **kw)


def codes(staff: StaffMember, s: ProposedShift) -> set[str]:
    return {f.code for f in evaluate(CheckContext(RULES, staff, s, NOW), COVER).findings}


def test_free_person_passes():
    assert codes(person(1), shift(MONDAY, 7, 15)) == set()


def test_weekly_limit_blocks_41st_hour():
    p = person(1, bookings=[booking(MONDAY + timedelta(days=i), 7, 15) for i in range(1, 5)])  # 32h
    assert "max_hours_week" not in codes(p, shift(MONDAY, 7, 15))  # 40h exactly is fine
    p.bookings.append(booking(MONDAY + timedelta(days=5), 18, 19))  # 33h
    assert "max_hours_week" in codes(p, shift(MONDAY, 7, 15))


def test_personal_weekly_limit_overrides_branch_rule():
    p = person(1, max_hours_per_week=16, bookings=[booking(MONDAY + timedelta(days=1), 7, 15)])
    assert "max_hours_week" not in codes(p, shift(MONDAY, 7, 15))
    p.bookings.append(booking(MONDAY + timedelta(days=2), 7, 15))
    assert "max_hours_week" in codes(p, shift(MONDAY, 7, 15))


def test_daily_limit_and_overlap():
    p = person(1, bookings=[booking(MONDAY, 7, 11)])
    assert "max_hours_day" in codes(p, shift(MONDAY, 14, 22))  # 4 + 8 > 8
    assert "overlap" in codes(p, shift(MONDAY, 10, 14))


def test_opening_hours_and_role_and_leave():
    assert "opening_hours" in codes(person(1), shift(MONDAY, 6, 14))
    assert "role" in codes(person(1, role=CHEF), shift(MONDAY, 7, 15))
    on_leave = person(1, leave=[LeaveBlock(MONDAY, MONDAY, "approved", "Annual")])
    assert "on_leave" in codes(on_leave, shift(MONDAY, 7, 15))
    pending = person(1, leave=[LeaveBlock(MONDAY, MONDAY, "pending", "Annual")])
    assert codes(pending, shift(MONDAY, 7, 15)) == {"pending_leave"}  # soft only


def test_back_to_back_is_a_warning_not_a_block():
    # closes Sunday 22:00, opens Monday 07:00 -> 9h rest < 10h minimum
    p = person(1, bookings=[booking(MONDAY - timedelta(days=1), 14, 22)])
    assert codes(p, shift(MONDAY, 7, 15)) == {"back_to_back"}


def test_max_days_per_week():
    p = person(1, bookings=[booking(MONDAY + timedelta(days=i), 7, 11) for i in range(1, 7)])  # 6 days, 24h
    assert "max_days_week" in codes(p, shift(MONDAY, 7, 11))


def test_ranking_prefers_lighter_week_and_lists_unavailable():
    busy = person(1, bookings=[booking(MONDAY + timedelta(days=i), 7, 15) for i in range(1, 4)])
    free = person(2)
    blocked = person(3, leave=[LeaveBlock(MONDAY, MONDAY, "approved", "Medical")])
    eligible, unavailable = rank_candidates(RULES, shift(MONDAY, 7, 15), [busy, free, blocked], NOW)
    assert [c.staff.id for c in eligible] == [2, 1]
    assert unavailable[0].staff.id == 3 and "medical" in unavailable[0].reasons[0]


def _seed_demands() -> list[PatternDemand]:
    weekday, weekend = frozenset(range(5)), frozenset({5, 6})
    out = []
    pid = 0
    for name, days, counts in [("Weekday", weekday, (1, 2, 2)), ("Weekend", weekend, (1, 3, 3))]:
        for label, s, e in [("morning", 7, 15), ("evening", 14, 22)]:
            pid += 1
            for role, n in zip((CASHIER, SERVER, CHEF), counts, strict=True):
                out.append(PatternDemand(pid, f"{name} {label}", time(s), time(e), days, role, str(role), n))
    return out


def test_generator_fills_seed_week_within_all_rules():
    staff = (
        [person(i, CASHIER) for i in range(1, 5)]
        + [person(i, SERVER) for i in range(5, 13)]
        + [person(i, CHEF) for i in range(13, 21)]
    )
    result = generate_week(RULES, MONDAY, _seed_demands(), staff, {}, NOW)
    assert result.gaps == []
    # 5 weekdays x 2 shifts x 5 people + 2 weekend days x 2 shifts x 7 people
    assert len(result.planned) == 5 * 2 * 5 + 2 * 2 * 7
    for p in staff:
        hours = sum(b.hours for b in p.bookings)
        assert hours <= RULES.max_hours_per_week
        assert len({b.day for b in p.bookings}) <= RULES.max_days_per_week
        for d in {b.day for b in p.bookings}:
            assert sum(b.hours for b in p.bookings if b.day == d) <= RULES.max_hours_per_day
    # hours are spread evenly within a role
    server_hours = [sum(b.hours for b in p.bookings) for p in staff if p.role_id == SERVER]
    assert max(server_hours) - min(server_hours) <= 8


def test_generator_reports_gap_with_reason():
    staff = [person(1, CASHIER)]
    result = generate_week(RULES, MONDAY, _seed_demands(), staff, {}, NOW)
    assert result.gaps, "one cashier cannot cover 14 shifts"
    assert any("Cashier" in g.role_name or g.role_name == "1" for g in result.gaps)
    assert all(g.reason for g in result.gaps)
