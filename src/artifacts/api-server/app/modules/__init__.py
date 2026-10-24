"""Feature modules. Each one is a folder with the same shape:

    models.py   its database tables
    schemas.py  its API request/response shapes
    service.py  its logic (bigger modules split this into several files)
    router.py   its HTTP routes

Modules may call each other's services. core/ does not depend on any module (apart from
create_tables() asking this package to load every table).
"""

from importlib import import_module

MODULES = ("accounts", "people", "scheduling", "leave", "cover", "notifications", "dashboard")


def load_models() -> None:
    """Import every module's tables so SQLAlchemy knows about all of them (needed before create_all)."""
    import_module("app.core.activity")
    for name in MODULES:
        try:
            import_module(f"app.modules.{name}.models")
        except ModuleNotFoundError as exc:
            if exc.name != f"app.modules.{name}.models":
                raise


def routers() -> list:
    return [import_module(f"app.modules.{name}.router").router for name in MODULES]
