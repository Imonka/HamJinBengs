"""End-to-end API tests on the demo data (see conftest.py)."""

from conftest import login


def test_health_and_auth(client, manager):
    assert client.get("/api/healthz").json() == {"status": "ok"}
    assert client.get("/api/dashboard/summary").status_code == 401
    assert client.post("/api/auth/login", json={"email": "farah@mamarich.my", "pin": "0000"}).status_code == 401
    staff = login(client, "aisyah@mamarich.my", "1111")
    assert client.get("/api/employees", headers=staff).status_code == 403
    assert client.get("/api/auth/me", headers=staff).json()["access"] == "staff"


def test_seeded_roster_respects_rules(client, manager):
    settings = client.get("/api/settings", headers=manager).json()
    far = client.get("/api/roster/week", params={"start": "2030-01-01"}, headers=manager).json()
    assert far["filled"] == 0 and far["gaps"] == far["required"] > 0  # demand exists, nobody rostered yet
    from datetime import date

    week = client.get("/api/roster/week", params={"start": date.today().isoformat()}, headers=manager).json()
    assert week["filled"] > 0
    for e in week["employees"]:
        assert e["hours"] <= e["maxHours"] <= settings["maxHoursPerWeek"]
        assert e["days"] <= settings["maxDaysPerWeek"]


def _fresh_case(client, manager, name: str):
    """Roster a far-future week, then give `name` approved leave on their first shift -> a new open case."""
    client.post("/api/roster/generate", headers=manager, json={"weekStart": "2030-01-14"})
    person = client.get("/api/employees", headers=manager, params={"search": name}).json()[0]
    shift = client.get("/api/shifts", headers=manager,
                       params={"from": "2030-01-14", "to": "2030-01-20", "employeeId": person["id"]}).json()[0]
    result = client.post("/api/leave", headers=manager, json={
        "employeeId": person["id"], "leaveType": "Annual", "startDate": shift["date"],
        "endDate": shift["date"], "status": "approved"}).json()
    case = result["coverageCases"][0]
    eligible = client.get(f"/api/coverage/{case['id']}/candidates", headers=manager).json()["eligible"]
    assert len(eligible) >= 2
    return case, eligible


def _token_for(client, candidate):
    return login(client, candidate["employee"]["email"], "1111")


def test_first_to_accept_gets_the_shift(client, manager):
    case, eligible = _fresh_case(client, manager, "nurul")
    a, b = eligible[0], eligible[1]
    r = client.post(f"/api/coverage/{case['id']}/offers", headers=manager,
                    json={"employeeIds": [a["employee"]["id"], b["employee"]["id"]]})
    assert r.status_code == 200 and r.json()["status"] == "offered"

    ta, tb = _token_for(client, a), _token_for(client, b)
    offer_a = next(o for o in client.get("/api/me/offers", headers=ta).json() if o["status"] == "pending")
    offer_b = next(o for o in client.get("/api/me/offers", headers=tb).json() if o["status"] == "pending")
    assert offer_a["canAccept"] and offer_a["hoursAfter"] > offer_a["hoursThisWeek"]

    assert client.post(f"/api/me/offers/{offer_a['id']}/accept", headers=ta).json()["status"] == "accepted"
    late = client.post(f"/api/me/offers/{offer_b['id']}/accept", headers=tb)
    assert late.status_code == 409 and "someone else" in late.json()["error"].lower()

    filled = client.get(f"/api/coverage/{case['id']}", headers=manager).json()
    assert filled["status"] == "filled"
    assert filled["replacementEmployee"]["id"] == a["employee"]["id"]
    assert filled["shift"]["status"] == "covered"
    mine = client.get("/api/me/shifts", headers=ta, params={"from": filled["shift"]["date"],
                                                            "to": filled["shift"]["date"]}).json()
    assert any(s["source"] == "cover" for s in mine)


def test_decline_reopens_case(client, manager):
    case, eligible = _fresh_case(client, manager, "priya")
    who = eligible[0]
    client.post(f"/api/coverage/{case['id']}/offers", headers=manager, json={"employeeIds": [who["employee"]["id"]]})
    t = _token_for(client, who)
    offer = next(o for o in client.get("/api/me/offers", headers=t).json()
                 if o["status"] == "pending" and o["shift"]["coverCaseId"] == case["id"])
    r = client.post(f"/api/me/offers/{offer['id']}/decline", headers=t, json={"note": "Busy"})
    assert r.json()["status"] == "declined"
    assert client.get(f"/api/coverage/{case['id']}", headers=manager).json()["status"] == "open"


def test_manual_shift_rule_violation_and_override(client, manager):
    staff = client.get("/api/employees", headers=manager, params={"search": "kavitha"}).json()[0]
    body = {"employeeId": staff["id"], "roleId": staff["roleId"], "date": "2030-01-07",
            "startTime": "05:00", "endTime": "15:00"}
    r = client.post("/api/shifts", headers=manager, json=body)
    assert r.status_code == 409 and r.json()["violations"]
    r = client.post("/api/shifts", headers=manager, json={**body, "override": True})
    assert r.status_code == 201
    assert client.delete(f"/api/shifts/{r.json()['id']}", headers=manager).status_code == 204


def test_add_employee_and_generate(client, manager):
    role = client.post("/api/roles", headers=manager, json={"name": "Runner"}).json()
    r = client.post("/api/employees", headers=manager,
                    json={"name": "Test Runner", "email": "runner@mamarich.my", "pin": "4321", "roleId": role["id"]})
    assert r.status_code == 201
    client.post("/api/shift-patterns", headers=manager, json={
        "name": "Runner", "startTime": "10:00", "endTime": "14:00", "days": [0, 1, 2, 3, 4, 5, 6],
        "requirements": [{"roleId": role["id"], "headcount": 1}]})
    result = client.post("/api/roster/generate", headers=manager,
                         json={"weekStart": "2030-01-07"}).json()
    runner = next(e for e in result["employees"] if e["name"] == "Test Runner")
    assert runner["hours"] == 24  # 6 days x 4h: the 7th day is blocked by the max-days rule
    assert any("days-per-week" in g["reason"] for g in result["gaps"])
