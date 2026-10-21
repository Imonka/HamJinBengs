"""Environment configuration. Everything the server needs from the outside world lives here."""

import os
from dataclasses import dataclass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be set (PostgreSQL connection string).")
    # SQLAlchemy needs to be told to use the psycopg (v3) driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class Config:
    database_url: str
    session_days: int = 30
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    log_sql: bool = False


def load_config() -> Config:
    return Config(
        database_url=_database_url(),
        session_days=int(os.environ.get("SESSION_DAYS", "30")),
        log_sql=os.environ.get("LOG_SQL") == "1",
    )


config = load_config()
