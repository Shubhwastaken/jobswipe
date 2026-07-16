"""Shared test fixtures.

The app connects to the DB and runs load_data() at import, so importing it
requires a reachable database. Tests that need it are marked @requires_db and
skip (never fail) when DATABASE_URL is unset or unreachable — that is how they
behave in CI without the secret. The pure-unit tests (skill normalizer, overlap)
import none of this and always run.

We use FastAPI's in-process TestClient rather than a live uvicorn on a port:
no port to bind, no stale-server-from-a-previous-run false pass.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load backend/.env so DATABASE_URL / GROQ_API_KEY are visible before we decide
# whether the DB-backed tests can run. In CI these come from the environment
# (secrets) instead, and load_dotenv is a harmless no-op.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Test-only environment, set before the app is imported by any fixture:
#   - ENABLE_TRIAL_LOGIN lets a test authenticate as a seeded student with the
#     shared trial password. This is a dev/test affordance; production leaves it
#     off (default false). It is NOT a statement that trial login is safe.
#   - PROFILE_SOURCE=db exercises the path that actually ships.
os.environ.setdefault("ENABLE_TRIAL_LOGIN", "true")
os.environ.setdefault("PROFILE_SOURCE", "db")

TRIAL_PASSWORD = "Test123"
SEED_STUDENT_ID = "S0001"
SEED_EMAIL = "amazon.student1@srmist.edu.in"
SECOND_STUDENT_ID = "S0002"
SECOND_EMAIL = "amazon.student2@srmist.edu.in"


def _db_available() -> bool:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return False
    try:
        import psycopg2

        conn = psycopg2.connect(dsn, connect_timeout=8)
        conn.close()
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_available()

# Decorator for tests that need the database / the full app.
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set or unreachable")


@pytest.fixture(scope="session")
def client():
    if not DB_AVAILABLE:
        pytest.skip("database unavailable")
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
def login(client):
    """Return a function that logs a student in and yields their bearer token."""

    def _login(email: str = SEED_EMAIL, password: str = TRIAL_PASSWORD) -> str:
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _login


@pytest.fixture
def auth_headers(login):
    def _headers(email: str = SEED_EMAIL, password: str = TRIAL_PASSWORD) -> dict:
        return {"Authorization": f"Bearer {login(email, password)}"}

    return _headers


def db_connect():
    """A raw psycopg2 connection for tests that need to seed/clean up rows."""
    import psycopg2

    return psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=15)
