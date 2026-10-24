"""API tests run against the real PostgreSQL database but inside a separate schema
("cover_test"), so they never touch the app's own data."""

import os

import psycopg
import pytest

TEST_SCHEMA = "cover_test"


def _with_search_path(url: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}options=-csearch_path%3D{TEST_SCHEMA}"


_base_url = os.environ["DATABASE_URL"]
with psycopg.connect(_base_url, autocommit=True) as conn:
    conn.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
    conn.execute(f"CREATE SCHEMA {TEST_SCHEMA}")
os.environ["DATABASE_URL"] = _with_search_path(_base_url)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.core.db import SessionLocal
    from app.main import app
    from app.seed import reset_database, seed

    reset_database()
    with SessionLocal() as db:
        seed(db)
    with TestClient(app) as c:
        yield c

    from app.core.db import engine

    engine.dispose()
    with psycopg.connect(_base_url, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")


def login(client, email: str, pin: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "pin": pin})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="session")
def manager(client):
    return login(client, "farah@mamarich.my", "1234")
