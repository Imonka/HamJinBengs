"""Cover cases and cover offers.

Flow:
  1. Approved leave opens a cover case for each affected shift (see leave.py).
  2. The manager opens the case and sees `candidates()`: everyone with the same role, ranked,
     plus who is unavailable and why.
  3. The manager ticks one or more people and calls `send_offers()`. Each gets a notification.
  4. Each person accepts or declines from their own screen. The FIRST to accept gets the
     shift; everyone else's offer expires and they're told it's been taken.
  5. The manager can withdraw an offer, or cancel the case (leave the shift unstaffed).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..errors import BadRequest, Conflict, NotFound, RuleViolation
from ..models import CoverageCase, CoverOffer, Employee, Shift
from ..scheduling import ProposedShift, Rules, check_person, rank_candidates
from ..timeutil import fmt_window, now_utc
from . import activity
from .notifications import notify, notify_managers
from .serializers import case_out, employee_ref, shift_out
from .settings import get_rules
from .staffing import load_staff

LIVE = ("open", "offered")


# ------------------------------------------------------------------ reading
def get_case(db: Session, case_id: int, lock: bool = False) -> CoverageCase:
    if lock:  # manager actions queue on the same row lock as employee accept/decline
        case = db.scalar(select(CoverageCase).where(CoverageCase.id == case_id)
                         .with_for_update(of=CoverageCase).execution_options(populate_existing=True))
    else:
        case = db.get(CoverageCase, case_id)
    if case is None:
        raise NotFound("Cover case not found.")
    return case


def list_cases(db: Session, status: str | None) -> list[schemas.CoverageCase]:
    q = select(CoverageCase).join(CoverageCase.shift)
    if status:
        q = q.where(CoverageCase.status == status)
    rows = db.scalars(q.order_by(Shift.starts_at, CoverageCase.id)).unique().all()
    tz = get_rules(db).tz
    return [case_out(c, tz) for c in rows]


def case_detail(db: Session, case_id: int) -> schemas.CoverageCase:
    return case_out(get_case(db, case_id), get_rules(db).tz)


def _proposed(case: CoverageCase) -> ProposedShift:
    s = case.shift
    return ProposedShift(s.date, s.starts_at, s.ends_at, s.role_id, s.role.name)


def candidates(db: Session, case_id: int) -> schemas.CandidateList:
    case = get_case(db, case_id)
    if case.status not in LIVE:
        return schemas.CandidateList(eligible=[], unavailable=[])
    rules = get_rules(db)
    now = now_utc()
    pool = load_staff(db, rules, case.shift.date, role_id=case.shift.role_id,
                      exclude_ids=[case.original_employee_id], now=now)
    eligible, unavailable = rank_candidates(rules, _proposed(case), pool, now)

    latest_offer = {o.employee_id: o.status for o in case.offers}  # ordered by id, so last one wins
    people = {e.id: e for e in db.scalars(select(Employee).where(Employee.id.in_([p.id for p in pool])))}
    return schemas.CandidateList(
        eligible=[
            schemas.Candidate(
                employee=employee_ref(people[c.staff.id]), score=c.score,
                hours_worked_so_far=c.hours_worked_so_far, hours_this_week=c.hours_this_week,
                hours_after=c.hours_after, max_hours_per_week=c.weekly_limit,
                hours_that_day=c.hours_that_day, max_hours_per_day=rules.max_hours_per_day,
                days_this_week=c.days_this_week, max_days_per_week=rules.max_days_per_week,
                back_to_back=c.back_to_back, rest_hours_before=c.rest_before, rest_hours_after=c.rest_after,
                reasons=c.reasons, warnings=c.warnings, offer_status=latest_offer.get(c.staff.id),  # type: ignore[arg-type]
            )
            for c in eligible
        ],
        unavailable=[
            schemas.UnavailableCandidate(employee=employee_ref(people[u.staff.id]), reasons=u.reasons)
            for u in unavailable
        ],
    )


# ------------------------------------------------------------------ manager actions
def _require_live(case: CoverageCase) -> None:
    if case.status not in LIVE:
        raise Conflict(f"This cover case is already {case.status}.")
    if case.shift.starts_at <= now_utc():
        raise Conflict("This shift has already started.")


def send_offers(db: Session, case_id: int, data: schemas.SendOffersInput, actor: Employee) -> schemas.CoverageCase:
    case = get_case(db, case_id, lock=True)
    _require_live(case)
    rules = get_rules(db)
    ids = list(dict.fromkeys(data.employee_ids))
    if case.original_employee_id in ids:
        raise BadRequest(f"{case.original_employee.name} is the person on leave.")
    already = {o.employee_id for o in case.offers if o.status == "pending"}
    ids = [i for i in ids if i not in already]
    if not ids:
        raise Conflict("Everyone selected already has a pending offer for this shift.")

    staff = {p.id: p for p in load_staff(db, rules, case.shift.date, employee_ids=ids)}
    missing = [i for i in ids if i not in staff]
    if missing:
        raise BadRequest("Some selected people are not active employees.")
    proposed, now = _proposed(case), now_utc()
    problems = []
    for i in ids:
        _, blocked, _ = check_person(rules, proposed, staff[i], now)
        if blocked:
            problems.append(f"{staff[i].name}: {'; '.join(blocked)}")
    if problems:
        raise RuleViolation("Some people can't take this shift.", problems)

    window = fmt_window(case.shift.starts_at, case.shift.ends_at, rules.tz)
    message = (data.message or "").strip() or None
    names = []
    for i in ids:
        offer = CoverOffer(case_id=case.id, employee_id=i, status="pending", message=message)
        db.add(offer)
        db.flush()
        person = db.get(Employee, i)
        names.append(person.name)
        notify(
            db, person, audience="offered", kind="cover_offer",
            subject=f"Can you cover a {case.shift.role.name} shift? {window}",
            body=(f"{actor.name} is asking if you can cover {case.original_employee.name}'s shift, {window}. "
                  "Open the app to accept or decline. The first person to accept gets the shift."
                  + (f"\n\nMessage: {message}" if message else "")),
            case_id=case.id, offer_id=offer.id,
        )
    case.status = "offered"
    activity.log(db, "offers_sent", f"Asked {', '.join(names)} to cover {case.original_employee.name}, {window}")
    db.commit()
    db.refresh(case)
    return case_out(case, rules.tz)


def _reopen_if_no_pending(case: CoverageCase) -> None:
    if case.status == "offered" and not any(o.status == "pending" for o in case.offers):
        case.status = "open"


def reopen_cases_without_offers(db: Session) -> None:
    for case in db.scalars(select(CoverageCase).where(CoverageCase.status == "offered")):
        _reopen_if_no_pending(case)


def withdraw_offer(db: Session, case_id: int, offer_id: int) -> schemas.CoverageCase:
    case = get_case(db, case_id, lock=True)
    offer = db.get(CoverOffer, offer_id)
    if offer is None or offer.case_id != case.id:
        raise NotFound("Offer not found.")
    if offer.status != "pending":
        raise Conflict(f"This offer is already {offer.status}.")
    rules = get_rules(db)
    offer.status, offer.responded_at = "withdrawn", now_utc()
    window = fmt_window(case.shift.starts_at, case.shift.ends_at, rules.tz)
    notify(db, offer.employee, audience="offered", kind="offer_withdrawn",
           subject=f"Cover request withdrawn: {window}",
           body=f"You no longer need to cover the {case.shift.role.name} shift on {window}. Thank you.",
           case_id=case.id, offer_id=offer.id)
    db.flush()
    db.refresh(case)
    _reopen_if_no_pending(case)
    activity.log(db, "offer_withdrawn", f"Withdrew cover request to {offer.employee.name}")
    db.commit()
    return case_out(case, rules.tz)


def cancel_case(db: Session, case_id: int) -> schemas.CoverageCase:
    case = get_case(db, case_id, lock=True)
    if case.status not in LIVE:
        raise Conflict(f"This cover case is already {case.status}.")
    rules = get_rules(db)
    now = now_utc()
    window = fmt_window(case.shift.starts_at, case.shift.ends_at, rules.tz)
    for o in case.offers:
        if o.status == "pending":
            o.status, o.responded_at = "withdrawn", now
            notify(db, o.employee, audience="offered", kind="offer_withdrawn",
                   subject=f"Cover request withdrawn: {window}",
                   body=f"You no longer need to cover the {case.shift.role.name} shift on {window}.",
                   case_id=case.id, offer_id=o.id)
    case.status, case.closed_at = "cancelled", now
    case.shift.status = "cancelled"
    activity.log(db, "cover_cancelled",
                 f"Cover cancelled for {case.original_employee.name}, {window}; shift left unstaffed")
    db.commit()
    db.refresh(case)
    return case_out(case, rules.tz)


# ------------------------------------------------------------------ employee actions
def _lock_my_offer(db: Session, offer_id: int, user: Employee) -> tuple[CoverOffer, CoverageCase]:
    """Lock the CASE first, then the offer. Everyone touching the same case queues on the case
    row in the same order, so simultaneous accepts can't deadlock: the second waits, then sees
    the case already filled."""
    case_id = db.scalar(select(CoverOffer.case_id).where(CoverOffer.id == offer_id,
                                                         CoverOffer.employee_id == user.id))
    if case_id is None:
        raise NotFound("Offer not found.")
    case = db.scalar(select(CoverageCase).where(CoverageCase.id == case_id)
                     .with_for_update(of=CoverageCase).execution_options(populate_existing=True))
    offer = db.scalar(select(CoverOffer).where(CoverOffer.id == offer_id)
                      .with_for_update(of=CoverOffer).execution_options(populate_existing=True))
    return offer, case


def _not_pending(offer: CoverOffer, case: CoverageCase) -> Conflict:
    if offer.status == "expired" and case.status == "filled":
        return Conflict("Sorry, someone else has already taken this shift.")
    return Conflict(f"This offer is already {offer.status}.")


def my_offer_out(db: Session, offer: CoverOffer, rules: Rules) -> schemas.MyOffer:
    case = offer.case
    now = now_utc()
    proposed = ProposedShift(case.shift.date, case.shift.starts_at, case.shift.ends_at, case.shift.role_id,
                             case.shift.role.name,
                             ignore_shift_id=case.replacement_shift_id if offer.status == "accepted" else None)
    staff = load_staff(db, rules, case.shift.date, employee_ids=[offer.employee_id], active_only=False, now=now)
    ctx, blocked, _ = check_person(rules, proposed, staff[0], now)

    blocked_reason = None
    if offer.status == "pending":
        if case.status not in LIVE:
            blocked_reason = "Someone else has already taken this shift."
        elif case.shift.starts_at <= now:
            blocked_reason = "This shift has already started."
        elif blocked:
            blocked_reason = blocked[0]
    return schemas.MyOffer(
        id=offer.id, status=offer.status, message=offer.message,  # type: ignore[arg-type]
        created_at=offer.created_at, responded_at=offer.responded_at,
        shift=shift_out(case.shift, rules.tz, {case.shift_id: case.id}),
        covering_for=case.original_employee.name, case_status=case.status,  # type: ignore[arg-type]
        can_accept=offer.status == "pending" and blocked_reason is None,
        blocked_reason=blocked_reason,
        hours_this_week=ctx.hours_this_week,
        hours_after=ctx.hours_this_week if offer.status == "accepted" else ctx.hours_after,
        max_hours_per_week=ctx.weekly_limit,
    )


def my_offers(db: Session, user: Employee, status: str | None) -> list[schemas.MyOffer]:
    q = select(CoverOffer).where(CoverOffer.employee_id == user.id)
    if status:
        q = q.where(CoverOffer.status == status)
    rules = get_rules(db)
    offers = db.scalars(q.order_by(CoverOffer.created_at.desc()).limit(100)).all()
    return [my_offer_out(db, o, rules) for o in offers]


def accept_offer(db: Session, offer_id: int, user: Employee) -> schemas.MyOffer:
    """First come, first served. Row locks (case -> offer -> employee) make two people
    accepting at the same moment safe: the second one waits, then sees the case is filled."""
    offer, case = _lock_my_offer(db, offer_id, user)
    if offer.status != "pending":
        raise _not_pending(offer, case)
    db.scalar(select(Employee).where(Employee.id == user.id).with_for_update(of=Employee))
    rules = get_rules(db)
    now = now_utc()
    window = fmt_window(case.shift.starts_at, case.shift.ends_at, rules.tz)

    def expire(reason: str) -> Conflict:
        offer.status, offer.responded_at, offer.response_note = "expired", now, reason
        db.commit()
        return Conflict(reason)

    if case.status not in LIVE:
        raise expire("Sorry, someone else has already taken this shift.")
    if case.shift.starts_at <= now:
        raise expire("This shift has already started.")
    staff = load_staff(db, rules, case.shift.date, employee_ids=[user.id], now=now)
    _, blocked, _ = check_person(rules, _proposed(case), staff[0], now) if staff else (None, ["Not active"], None)
    if blocked:
        notify_managers(db, kind="offer_failed", subject=f"{user.name} couldn't accept cover: {window}",
                        body=f"{user.name} tried to accept but can no longer take it: {'; '.join(blocked)}.",
                        case_id=case.id, offer_id=offer.id)
        offer.status, offer.responded_at, offer.response_note = "expired", now, "; ".join(blocked)
        db.flush()
        db.refresh(case)
        _reopen_if_no_pending(case)
        db.commit()
        raise Conflict("You can no longer take this shift: " + "; ".join(blocked))

    # --- success: give them the shift
    original = case.shift
    replacement = Shift(
        employee_id=user.id, role_id=original.role_id, pattern_id=original.pattern_id, date=original.date,
        starts_at=original.starts_at, ends_at=original.ends_at, status="scheduled", source="cover",
        notes=f"Covering for {case.original_employee.name}",
    )
    db.add(replacement)
    db.flush()
    original.status = "covered"
    case.status, case.filled_at = "filled", now
    case.replacement_employee_id, case.replacement_shift_id = user.id, replacement.id
    offer.status, offer.responded_at = "accepted", now

    for other in case.offers:
        if other.id != offer.id and other.status == "pending":
            other.status, other.responded_at = "expired", now
            notify(db, other.employee, audience="offered", kind="offer_taken",
                   subject=f"Shift already covered: {window}",
                   body=f"{user.name} accepted first, so you don't need to cover {window}. Thanks for your help.",
                   case_id=case.id, offer_id=other.id)

    notify(db, user, audience="replacement", kind="cover_confirmed",
           subject=f"Confirmed: you're covering {window}",
           body=f"You're now rostered as {original.role.name}, {window}, covering for {case.original_employee.name}.",
           case_id=case.id, offer_id=offer.id)
    notify(db, case.original_employee, audience="original", kind="cover_found",
           subject=f"Your shift is covered: {window}",
           body=f"{user.name} will cover your {original.role.name} shift on {window}. Enjoy your leave.",
           case_id=case.id)
    teammates = db.scalars(select(Employee).join(Shift, Shift.employee_id == Employee.id).where(
        Shift.status == "scheduled", Shift.starts_at < original.ends_at, Shift.ends_at > original.starts_at,
        Employee.id.notin_([user.id, case.original_employee_id]), Employee.active.is_(True),
    )).unique().all()
    for t in teammates:
        notify(db, t, audience="team", kind="team_change", subject=f"Shift change: {window}",
               body=f"{user.name} is covering for {case.original_employee.name} ({original.role.name}) on {window}.",
               case_id=case.id)
    notify_managers(db, kind="cover_filled", subject=f"Covered: {case.original_employee.name}, {window}",
                    body=f"{user.name} accepted and is now rostered for {window}.", case_id=case.id,
                    offer_id=offer.id)
    activity.log(db, "cover_filled", f"{user.name} accepted cover for {case.original_employee.name}, {window}")
    db.commit()
    db.refresh(offer)
    return my_offer_out(db, offer, rules)


def decline_offer(db: Session, offer_id: int, user: Employee, note: str | None) -> schemas.MyOffer:
    offer, case = _lock_my_offer(db, offer_id, user)
    if offer.status != "pending":
        raise _not_pending(offer, case)
    rules = get_rules(db)
    offer.status, offer.responded_at = "declined", now_utc()
    offer.response_note = (note or "").strip() or None
    window = fmt_window(case.shift.starts_at, case.shift.ends_at, rules.tz)
    db.flush()
    db.refresh(case)
    _reopen_if_no_pending(case)
    notify_managers(db, kind="offer_declined", subject=f"{user.name} declined cover: {window}",
                    body=f"{user.name} can't cover {case.original_employee.name}, {window}."
                         + (f' Note: "{offer.response_note}"' if offer.response_note else "")
                         + (" Nobody else has been asked yet." if case.status == "open" else ""),
                    case_id=case.id, offer_id=offer.id)
    activity.log(db, "offer_declined", f"{user.name} declined cover for {case.original_employee.name}, {window}")
    db.commit()
    db.refresh(offer)
    return my_offer_out(db, offer, rules)
