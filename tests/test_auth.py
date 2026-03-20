# tests/test_auth.py — API key authentication tests

import pytest
from fastapi.testclient import TestClient
import app.main as main_module
from app.main import app


def test_auth_disabled_when_api_key_empty(client):
    """When API_KEY is empty, all endpoints are accessible without a header."""
    resp = client.get("/prospects")
    assert resp.status_code == 200


def test_auth_rejects_missing_key(monkeypatch):
    """When API_KEY is set, requests without the header get 401."""
    monkeypatch.setattr(main_module.settings, "API_KEY", "secret123")
    with TestClient(app) as c:
        resp = c.get("/prospects")
    assert resp.status_code == 401


def test_auth_rejects_wrong_key(monkeypatch):
    """Wrong key value returns 401."""
    monkeypatch.setattr(main_module.settings, "API_KEY", "correct-key")
    with TestClient(app) as c:
        resp = c.get("/prospects", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_auth_accepts_correct_key(monkeypatch):
    """Correct key returns 200."""
    monkeypatch.setattr(main_module.settings, "API_KEY", "correct-key")
    with TestClient(app) as c:
        resp = c.get("/prospects", headers={"X-API-Key": "correct-key"})
    assert resp.status_code == 200
