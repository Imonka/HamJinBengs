"""Account boundaries (managers vs. self-service), the earliest-first cover queue and the leave cover preview."""

from conftest import login


def _new_staff(client, manager, email: str, pin: str = "5678") -> dict:
    r = client.post("/api/employees", headers=manager, json={"name": "Boundary Test", "email": email, "pin": pin})
    assert r.status_code == 201, r.text
    return r.json()


def test_new_accounts_are_always_staff(client, manager):
    created = _new_staff(client, manager, "boundary1@mamarich.my")
    assert created["access"] == "staff"
    # trying to sneak manager access in is rejected, not silently ignored
    r = client.post("/api/employees", headers=manager,
                    json={"name": "Sneaky", "email": "sneaky@mamarich.my", "pin": "1234", "access": "manager"})
    assert r.status_code in (400, 422)
    imp = client.post("/api/employees/import", headers=manager,
                      json={"rows": [{"name": "Csv", "email": "csv1@mamarich.my", "pin": "1234", "access": "manager"}]})
    assert imp.status_code in (400, 422)
    imp = client.post("/api/employees/import", headers=manager,
                      json={"rows": [{"name": "Csv", "email": "csv1@mamarich.my", "pin": "1234"}]})
    assert imp.json()["created"] == 1
    csv = client.get("/api/employees", headers=manager, params={"search": "csv1@"}).json()[0]
    assert csv["access"] == "staff"


def test_manager_can_only_change_work_settings(client, manager):
    e = _new_staff(client, manager, "boundary2@mamarich.my")
    work = {"roleId": None, "maxHoursPerWeek": 30, "orbyteId": "ORB-BND2", "active": True}
    r = client.put(f"/api/employees/{e['id']}", headers=manager, json=work)
    assert r.status_code == 200 and r.json()["maxHoursPerWeek"] == 30 and r.json()["orbyteId"] == "ORB-BND2"

    for extra in ({"name": "Renamed"}, {"email": "x@mamarich.my"}, {"phone": "123"}, {"access": "manager"}, {"pin": "9999"}):
        r = client.put(f"/api/employees/{e['id']}", headers=manager, json={**work, **extra})
        assert r.status_code in (400, 422), extra
    after = client.get(f"/api/employees/{e['id']}", headers=manager).json()["employee"]
    assert after["name"] == "Boundary Test" and after["email"] == "boundary2@mamarich.my" and after["access"] == "staff"

    # the manager PIN-reset endpoint is gone
    assert client.put(f"/api/employees/{e['id']}/pin", headers=manager, json={"pin": "0000"}).status_code in (404, 405)
    assert login(client, "boundary2@mamarich.my", "5678")["Authorization"]


def test_people_edit_their_own_details(client, manager):
    _new_staff(client, manager, "boundary3@mamarich.my")
    me = login(client, "boundary3@mamarich.my", "5678")
    r = client.put("/api/auth/profile", headers=me, json={"name": "Self Named", "email": "boundary3@mamarich.my", "phone": "+60 12-000 1111"})
    assert r.status_code == 200 and r.json()["name"] == "Self Named" and r.json()["phone"] == "+60 12-000 1111"

    # changing the sign-in email needs the current PIN
    r = client.put("/api/auth/profile", headers=me, json={"name": "Self Named", "email": "boundary3b@mamarich.my"})
    assert r.status_code == 400
    r = client.put("/api/auth/profile", headers=me, json={"name": "Self Named", "email": "boundary3b@mamarich.my", "currentPin": "0000"})
    assert r.status_code == 400
    r = client.put("/api/auth/profile", headers=me, json={"name": "Self Named", "email": "boundary3b@mamarich.my", "currentPin": "5678"})
    assert r.status_code == 200 and r.json()["email"] == "boundary3b@mamarich.my"
    # can't take a colleague's email, can't change own access
    assert client.put("/api/auth/profile", headers=me, json={"name": "x", "email": "farah@mamarich.my", "currentPin": "5678"}).status_code == 409
    assert client.put("/api/auth/profile", headers=me, json={"name": "x", "email": "boundary3b@mamarich.my", "access": "manager"}).status_code in (400, 422)
    assert client.get("/api/auth/me", headers=me).json()["access"] == "staff"


def test_cli_access_and_pin_recovery(client, manager):
    from app.core.db import SessionLocal
    from app.core.errors import Conflict
    from app.modules.accounts.service import reset_pin, set_access

    _new_staff(client, manager, "boundary4@mamarich.my")
    with SessionLocal() as db:
        assert set_access(db, "boundary4@mamarich.my", "manager").access == "manager"
        assert set_access(db, "boundary4@mamarich.my", "staff").access == "staff"
        reset_pin(db, "boundary4@mamarich.my", "2468")
        try:
            set_access(db, "farah@mamarich.my", "staff")  # the only manager
            raise AssertionError("expected the last-manager guard")
        except Conflict:
            db.rollback()
    assert login(client, "boundary4@mamarich.my", "2468")["Authorization"]


def test_unfilled_queue_is_one_list_earliest_first(client, manager):
    unfilled = client.get("/api/coverage", headers=manager, params={"unfilled": "true"}).json()
    statuses = {c["status"] for c in unfilled}
    assert statuses <= {"open", "offered"}
    open_ = client.get("/api/coverage", headers=manager, params={"status": "open"}).json()
    offered = client.get("/api/coverage", headers=manager, params={"status": "offered"}).json()
    assert len(unfilled) == len(open_) + len(offered)
    starts = [c["shift"]["startsAt"] for c in unfilled]
    assert starts == sorted(starts)


def test_leave_cover_preview_before_deciding(client, manager):
    client.post("/api/roster/generate", headers=manager, json={"weekStart": "2030-02-04"})
    person = client.get("/api/employees", headers=manager, params={"search": "aisyah"}).json()[0]
    shifts = client.get("/api/shifts", headers=manager,
                        params={"from": "2030-02-04", "to": "2030-02-10", "employeeId": person["id"]}).json()
    assert shifts
    lv = client.post("/api/leave", headers=manager, json={
        "employeeId": person["id"], "leaveType": "Annual", "startDate": "2030-02-04",
        "endDate": "2030-02-10", "status": "pending"}).json()["leave"]
    cases_before = len(client.get("/api/coverage", headers=manager).json())

    preview = client.get(f"/api/leave/{lv['id']}/cover-preview", headers=manager).json()
    assert [p["shift"]["id"] for p in preview["shifts"]] == [s["id"] for s in shifts if s["status"] == "scheduled"]
    for p in preview["shifts"]:
        assert len(p["topCandidates"]) <= 3 and len(p["topCandidates"]) <= p["eligibleCount"]
        assert all(c["employee"]["id"] != person["id"] for c in p["topCandidates"])
        scores = [c["score"] for c in p["topCandidates"]]
        assert scores == sorted(scores, reverse=True)
    # read-only: nothing opened, the shifts are untouched
    assert len(client.get("/api/coverage", headers=manager).json()) == cases_before

    staff = login(client, "aisyah@mamarich.my", "1111")
    assert client.get(f"/api/leave/{lv['id']}/cover-preview", headers=staff).status_code == 403

    approved = client.post(f"/api/leave/{lv['id']}/approve", headers=manager).json()
    assert len(approved["coverageCases"]) == len(preview["shifts"])
    assert client.get(f"/api/leave/{lv['id']}/cover-preview", headers=manager).status_code == 409
