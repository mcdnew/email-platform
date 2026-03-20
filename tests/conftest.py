# tests/conftest.py — shared fixtures for the email-platform test suite

import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

# Force test environment before importing app modules
os.environ["API_KEY"] = ""          # auth disabled in tests
os.environ["TIMEZONE"] = "UTC"
os.environ["TRACKING_BASE_URL"] = "http://testserver"
os.environ["DATABASE_URL"] = "sqlite://"  # in-memory

from app.database import get_session
from app.main import app

# ── In-memory SQLite engine shared across all tests ──────────────────────────
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(TEST_ENGINE) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def reset_db():
    """Create all tables before each test, drop them after."""
    SQLModel.metadata.create_all(TEST_ENGINE)
    yield
    SQLModel.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with Session(TEST_ENGINE) as session:
        yield session
