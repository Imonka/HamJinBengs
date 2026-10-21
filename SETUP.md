# Leave Cover Scheduler ("Gantian"): setup and running guide

The app has three parts:

| Part | Folder | What it does |
| --- | --- | --- |
| Database | PostgreSQL | Stores roles, staff, shift patterns, shifts, leave, cover cases, offers, notifications, activity log, branch rules |
| Back end (API) | `artifacts/api-server` | **Python (FastAPI + SQLAlchemy).** All business logic: roster generation, rule checks, cover suggestions, offers. Serves everything under `/api` |
| Web app | `artifacts/cover-scheduler` | React screens for the manager and the staff portal. Calls the API at `/api/...` |

Shared code in `lib/`:
- `lib/api-spec/openapi.yaml` is the API contract.
- `lib/api-client-react` and `lib/api-zod` are generated from that contract for the web app. Don't edit them by hand.

`artifacts/mockup-sandbox` is a Replit design-preview tool. The app doesn't need it.

---

## 1. What you need installed

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12 or newer (tested on 3.13) | Back end |
| Node.js | 24.x | Web app only |
| pnpm | 10.x | `npm install -g pnpm` or `corepack enable` |
| PostgreSQL | 14 or newer | Local, Docker, or hosted (Neon, Supabase, RDS, ...) |

**Windows:** use **WSL** or **Git Bash**.

## 2. Environment variables

| Variable | Used by | Example | Required |
| --- | --- | --- | --- |
| `DATABASE_URL` | Back end | `postgresql://user:pass@localhost:5432/cover_scheduler` | Yes |
| `PORT` | Back end | `8080` | Optional (default 8080) |
| `SESSION_DAYS` | Back end | `30` | Optional. How long a sign-in lasts |
| `LOG_SQL` | Back end | `1` | Optional. Prints every SQL query |
| `PORT` | Web app (dev server) | `5173` | Yes (different from the API port) |
| `BASE_PATH` | Web app | `/` | Yes |
| `API_PROXY_TARGET` | Web app | `http://localhost:8080` | Yes outside Replit. Forwards the page's `/api` calls to the back end |

No API keys are needed. Email/WhatsApp and Orbyte are not connected yet: notifications are saved with status `queued` and shown in the app.

## 3. First-time setup

```bash
# from the project root
pip install -r artifacts/api-server/requirements.txt
pnpm install

export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/cover_scheduler"

cd artifacts/api-server
python -m app.cli init-db     # create the tables (safe to run again)
python -m app.cli seed        # OPTIONAL: demo data. WARNING: wipes all tables first
```

The demo data ("Kopi Lane — Mid Valley", 20 staff) uses dates relative to today, so it always looks current.
Demo sign-ins: manager `farah@kopilane.my` / PIN `1234`; staff `<firstname>@kopilane.my` / PIN `1111` (e.g. `aisyah@kopilane.my`).

To start clean instead: run `init-db` only, then create the first manager:

```bash
python -m app.cli add-employee --name "Your Name" --email you@company.my --pin 1234 --access manager
```

Then sign in and set up roles, shift patterns and branch rules on the **Setup** page.

## 4. Run it (development)

Two terminals.

**Terminal 1: back end**
```bash
cd artifacts/api-server
export DATABASE_URL="..."
python -m uvicorn app.main:app --port 8080 --reload --reload-dir app
```
Check it: http://localhost:8080/api/healthz returns `{"status":"ok"}`. Interactive API docs: http://localhost:8080/api/docs

**Terminal 2: web app** (from the project root)
```bash
PORT=5173 BASE_PATH=/ API_PROXY_TARGET=http://localhost:8080 \
  pnpm --filter @workspace/cover-scheduler run dev
```
Open http://localhost:5173

## 5. Run it (production / your own server)

```bash
# back end (keep it running with systemd, pm2, Docker, etc.)
DATABASE_URL="..." python -m uvicorn app.main:app --app-dir artifacts/api-server --host 0.0.0.0 --port 8080

# web app: build static files into artifacts/cover-scheduler/dist/public
pnpm --filter @workspace/cover-scheduler run build
```

Serve the web files and the API from the **same domain**, with `/api` forwarded to the back end. Example nginx:

```nginx
server {
  listen 80;
  root /path/to/artifacts/cover-scheduler/dist/public;
  location /api/ { proxy_pass http://127.0.0.1:8080; }
  location /     { try_files $uri /index.html; }
}
```

## 6. Command-line tools

Run from `artifacts/api-server`:

| Command | What it does |
| --- | --- |
| `python -m app.cli init-db` | Create missing tables |
| `python -m app.cli seed` | Wipe everything and load the demo |
| `python -m app.cli add-employee --name "Lina Ho" --email lina@x.my --pin 2222 --role Server [--max-hours 20] [--orbyte-id KL-0123]` | Add one employee |
| `python -m app.cli import-employees staff.csv` | Add many. CSV columns: `name,email,pin,role,access,max_hours,orbyte_id,phone` |
| `python -m app.cli generate --week 2026-11-02 [--replace]` | Build the roster for the week containing that date |
| `python -m pytest -q` | Run the tests (rule engine + API). API tests use a separate `cover_test` schema and don't touch your data |

## 7. How the back end is organised

```
artifacts/api-server/app/
  config.py        environment settings
  models/          database tables (people, roster, cover)
  schemas/         request/response shapes (match lib/api-spec/openapi.yaml)
  scheduling/      THE RULE ENGINE (pure Python, no database)
    constraints/   hard.py = rules that block, soft.py = rules that only warn/lower the score
                   __init__.py = DEFAULT_CONSTRAINTS list + "how to add a rule"
    generator.py   builds a week's roster from shift patterns
    ranking.py     scores replacement candidates
  services/        business actions (roster, leave, coverage, employees, ...)
    staffing.py    the ONE place that loads people + their hours/leave/shifts into the engine
    leave_sources.py  Orbyte plug-in point
  routers/         the HTTP endpoints
  seed.py, cli.py  demo data and command-line tools
```

## 8. Making changes

| You want to... | Do this |
| --- | --- |
| Change opening hours, 8h/day, 40h/week, max days, rest gap | Setup → Rules & branch in the app (stored in `branch_settings`). No code change |
| Change how many people each shift needs | Setup → Shift patterns |
| Give one person a lower weekly limit | Team → edit the person → weekly hour limit |
| **Add a new scheduling rule** (e.g. "never works Sundays") | Follow the 3 steps at the top of `app/scheduling/constraints/__init__.py`. The roster generator, cover suggestions, accepting offers and manual shift checks all pick it up automatically |
| Change how replacement candidates are scored | `app/scheduling/ranking.py` and penalty values in `constraints/soft.py` |
| Change notification wording | `app/services/coverage.py` and `app/services/notifications.py` |
| Actually send email/WhatsApp | `app/services/notifications.py` (`notify` writes the queued message; add a sender there) |
| Connect Orbyte live | Implement `OrbyteLeaveSource` in `app/services/leave_sources.py` and pass its records to `ingest_leave_records` (same path as the CSV import) |
| Add a database column/table | Add it in `app/models/`. `init-db` only creates missing tables; for changes to existing tables, run an `ALTER TABLE` (or add Alembic) |
| Add/change an endpoint | Update `lib/api-spec/openapi.yaml`, run `pnpm --filter @workspace/api-spec run codegen`, add the route in `app/routers/` |
| Check web app types | `pnpm run typecheck` |

## 9. Main API endpoints (all under `/api`)

- Sign-in: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PUT /auth/pin`
- Staff portal: `GET /me/shifts`, `GET /me/offers`, `POST /me/offers/{id}/accept`, `POST /me/offers/{id}/decline`, `GET /me/notifications`
- Setup: `GET/PUT /settings`, `GET/POST/PUT/DELETE /roles`, `GET/POST/PUT/DELETE /shift-patterns`
- Team: `GET/POST /employees`, `POST /employees/import`, `GET/PUT/DELETE /employees/{id}`, `PUT /employees/{id}/pin`
- Roster: `GET /roster/week`, `POST /roster/generate`, `GET/POST /shifts`, `PUT/DELETE /shifts/{id}`
- Leave: `GET/POST /leave`, `POST /leave/import`, `POST /leave/{id}/approve`, `POST /leave/{id}/reject`
- Cover: `GET /coverage`, `GET /coverage/{id}`, `GET /coverage/{id}/candidates`, `POST /coverage/{id}/offers`, `POST /coverage/{id}/offers/{offerId}/withdraw`, `POST /coverage/{id}/cancel`
- Overview: `GET /notifications`, `GET /dashboard/summary`, `GET /dashboard/activity`

Manager-only endpoints return 403 for staff.
