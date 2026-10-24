"""Command-line tools.

  python -m app.cli init-db                       create any missing tables
  python -m app.cli seed                          WIPE everything and load the demo data
  python -m app.cli add-employee --name "Ali" --email ali@x.my --pin 1111 --role Server [--access manager]
                                 [--max-hours 24] [--orbyte-id KL-0200] [--phone "+60..."]
  python -m app.cli import-employees staff.csv    columns: name,email,pin,role,max_hours,orbyte_id,phone (all staff)
  python -m app.cli set-access --email ali@x.my --access manager    grant/remove manager access
  python -m app.cli reset-pin --email ali@x.my --pin 2468           forgotten PIN recovery
  python -m app.cli generate --week 2026-10-26 [--replace]
"""

import argparse
import csv
import sys
from datetime import date

from app.core.db import create_tables, SessionLocal
from app.core.errors import AppError
from app.modules.people import schemas as people_schemas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sub.add_parser("seed")

    add = sub.add_parser("add-employee")
    add.add_argument("--name", required=True)
    add.add_argument("--email", required=True)
    add.add_argument("--pin", required=True)
    add.add_argument("--role")
    add.add_argument("--access", default="staff", choices=["staff", "manager"])
    add.add_argument("--max-hours", type=float)
    add.add_argument("--orbyte-id")
    add.add_argument("--phone")

    acc = sub.add_parser("set-access")
    acc.add_argument("--email", required=True)
    acc.add_argument("--access", required=True, choices=["staff", "manager"])

    pin = sub.add_parser("reset-pin")
    pin.add_argument("--email", required=True)
    pin.add_argument("--pin", required=True)

    imp = sub.add_parser("import-employees")
    imp.add_argument("csv_file")

    gen = sub.add_parser("generate")
    gen.add_argument("--week", required=True, type=date.fromisoformat, help="any date in the week")
    gen.add_argument("--replace", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "init-db":
        create_tables()
        print("Tables are ready.")
        return 0

    if args.cmd == "seed":
        from app.seed import reset_database, seed

        reset_database()
        with SessionLocal() as db:
            seed(db)
        print("Demo data loaded. Manager: farah@mamarich.my / 1234. Staff: aisyah@mamarich.my / 1111.")
        return 0

    from app.modules.accounts.service import reset_pin, set_access
    from app.modules.people.service import add_employee, import_employees

    with SessionLocal() as db:
        try:
            if args.cmd == "add-employee":
                e = add_employee(db, name=args.name, email=args.email, pin=args.pin, role_name=args.role,
                                 access=args.access, max_hours_per_week=args.max_hours,
                                 orbyte_id=args.orbyte_id, phone=args.phone)
                print(f"Added {e.name} (id {e.id}).")
            elif args.cmd == "set-access":
                e = set_access(db, args.email, args.access)
                print(f"{e.name} now has {e.access} access.")
            elif args.cmd == "reset-pin":
                e = reset_pin(db, args.email, args.pin)
                print(f"PIN reset for {e.name}. They have been signed out everywhere.")
            elif args.cmd == "import-employees":
                with open(args.csv_file, newline="", encoding="utf-8-sig") as f:
                    rows = [
                        people_schemas.EmployeeImportRow(
                            name=r.get("name", ""), email=r.get("email", ""), pin=r.get("pin", ""),
                            role_name=r.get("role") or None,
                            max_hours_per_week=float(r["max_hours"]) if r.get("max_hours") else None,
                            orbyte_id=r.get("orbyte_id") or None, phone=r.get("phone") or None,
                        )
                        for r in csv.DictReader(f)
                    ]
                result = import_employees(db, rows)
                print(f"Added {result.created} employee(s).")
                for err in result.errors:
                    print(f"  row {err.row}: {err.message}", file=sys.stderr)
            elif args.cmd == "generate":
                from app.modules.scheduling.roster import generate

                result = generate(db, args.week, args.replace)
                print(f"Week of {result.week_start}: {result.created} shift(s) added, {result.removed} replaced.")
                for g in result.gaps:
                    print(f"  gap {g.date} {g.pattern_name} {g.role_name} x{g.missing}: {g.reason}")
        except AppError as exc:
            print(f"Error: {exc.message}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
