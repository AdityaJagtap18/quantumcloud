"""Test configuration: SQLite + fakeredis instead of Postgres/Redis, set
BEFORE any `app.*` module is imported (Settings() reads env at import time).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_quantumcloud.db"
os.environ["REDIS_URL"] = "fakeredis://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.services.backend_service import seed_backends


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_backends(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("test_quantumcloud.db")
    except FileNotFoundError:
        pass


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    # Registration may already have happened in a previous test (session-scoped DB); that's fine.
    client.post("/api/auth/register", json={"email": "tester@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "tester@example.com", "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
