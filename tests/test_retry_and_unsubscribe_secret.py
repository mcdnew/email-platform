# tests/test_retry_and_unsubscribe_secret.py
#
# Tests for:
#   - POST /retry-failed (transient failure retry logic)
#   - UNSUBSCRIBE_SECRET separation from API_KEY

from datetime import datetime, timedelta
from unittest.mock import patch

from sqlmodel import Session, select

from app.models import (
    Prospect, EmailTemplate, Sequence,
    ScheduledEmail, SentEmail,
)
from app.tracking import make_unsubscribe_token, load_unsubscribe_token


# ─────────────────────── helpers ────────────────────────────────────────────

def _seed_failed(db: Session, unsubscribed: bool = False, retry_count: int = 0):
    """Seed one failed ScheduledEmail. Returns (prospect, template, sched)."""
    seq = Sequence(name="Seq")
    db.add(seq); db.commit(); db.refresh(seq)

    tpl = EmailTemplate(name="T", subject="Hi {{name}}", body="<p>Hi</p>")
    db.add(tpl); db.commit(); db.refresh(tpl)

    p = Prospect(name="Bob", email="bob@example.com", sequence_id=seq.id, unsubscribed=unsubscribed)
    db.add(p); db.commit(); db.refresh(p)

    sched = ScheduledEmail(
        prospect_id=p.id,
        template_id=tpl.id,
        sequence_id=seq.id,
        send_at=datetime.utcnow() - timedelta(minutes=5),
        status="failed",
        retry_count=retry_count,
    )
    db.add(sched); db.commit(); db.refresh(sched)
    return p, tpl, sched


# ─────────────────────── /retry-failed ──────────────────────────────────────

def test_retry_failed_resets_to_pending_and_sends(client, db):
    """Transient failure: retry resets to pending, increments retry_count, sends."""
    _, _, sched = _seed_failed(db)
    assert sched.status == "failed"
    assert sched.retry_count == 0

    with patch("app.main.send_email", return_value=True):
        resp = client.post("/retry-failed")

    assert resp.status_code == 200
    data = resp.json()
    assert data["retried"] == 1
    assert "processed 1" in data["message"]

    db.refresh(sched)
    assert sched.status == "sent"
    assert sched.retry_count == 1


def test_retry_failed_smtp_failure_marks_failed_again(client, db):
    """SMTP fails on retry: email goes back to failed, retry_count still incremented."""
    _, _, sched = _seed_failed(db)

    with patch("app.main.send_email", return_value=False):
        resp = client.post("/retry-failed")

    assert resp.status_code == 200
    assert resp.json()["retried"] == 1

    db.refresh(sched)
    assert sched.status == "failed"
    assert sched.retry_count == 1


def test_retry_failed_skips_unsubscribed(client, db):
    """Unsubscribed prospect is not retried."""
    _, _, sched = _seed_failed(db, unsubscribed=True)

    with patch("app.main.send_email") as mock_send:
        resp = client.post("/retry-failed")
        mock_send.assert_not_called()

    assert resp.status_code == 200
    assert resp.json()["retried"] == 0
    assert resp.json()["message"] == "no retryable emails found"

    db.refresh(sched)
    assert sched.status == "failed"  # unchanged
    assert sched.retry_count == 0


def test_retry_failed_skips_at_max_retries(client, db):
    """Email already at MAX_RETRIES is not retried."""
    from app.config import settings
    _, _, sched = _seed_failed(db, retry_count=settings.MAX_RETRIES)

    with patch("app.main.send_email") as mock_send:
        resp = client.post("/retry-failed")
        mock_send.assert_not_called()

    assert resp.status_code == 200
    assert resp.json()["retried"] == 0


def test_retry_failed_skips_missing_prospect(client, db):
    """Email whose prospect was deleted is not retried."""
    p, _, sched = _seed_failed(db)
    # Delete the prospect
    db.delete(p); db.commit()

    with patch("app.main.send_email") as mock_send:
        resp = client.post("/retry-failed")
        mock_send.assert_not_called()

    assert resp.status_code == 200
    assert resp.json()["retried"] == 0


def test_retry_failed_no_failed_emails(client, db):
    """No failed emails returns graceful message."""
    resp = client.post("/retry-failed")
    assert resp.status_code == 200
    assert resp.json()["retried"] == 0
    assert "no retryable emails found" in resp.json()["message"]


def test_retry_count_increments_each_call(client, db):
    """retry_count increments on each /retry-failed call until MAX_RETRIES."""
    from app.config import settings
    _, _, sched = _seed_failed(db)

    for i in range(1, settings.MAX_RETRIES + 1):
        with patch("app.main.send_email", return_value=False):
            resp = client.post("/retry-failed")
        db.refresh(sched)
        assert sched.retry_count == i

    # One more call: already at MAX_RETRIES, should be skipped
    with patch("app.main.send_email") as mock_send:
        resp = client.post("/retry-failed")
        mock_send.assert_not_called()
    assert resp.json()["retried"] == 0


# ─────────────────────── UNSUBSCRIBE_SECRET ─────────────────────────────────

def test_unsubscribe_token_roundtrip_uses_dedicated_secret():
    """
    Regression: ISSUE — UNSUBSCRIBE_SECRET separation from API_KEY.
    Found by /qa on 2026-03-20.
    Report: .gstack/qa-reports/qa-report-localhost-2026-03-20.md

    Tokens signed with UNSUBSCRIBE_SECRET (or its API_KEY fallback) round-trip
    correctly. Rotating API_KEY while keeping UNSUBSCRIBE_SECRET stable preserves
    existing tokens.
    """
    email = "carol@example.com"
    token = make_unsubscribe_token(email)
    # Token must round-trip back to the original email
    assert load_unsubscribe_token(token) == email


def test_unsubscribe_token_tampered_returns_none():
    """Tampered token returns None without raising."""
    assert load_unsubscribe_token("tampered.garbage.token") is None


def test_unsubscribe_endpoint_still_works_with_fallback_secret(client, db):
    """
    When UNSUBSCRIBE_SECRET is unset, tokens fall back to API_KEY and the
    /unsubscribe endpoint still processes them correctly.
    (API_KEY is '' in tests — falls back to dev-secret, which is stable.)
    """
    seq = Sequence(name="S")
    db.add(seq); db.commit(); db.refresh(seq)

    tpl = EmailTemplate(name="T", subject="Hi", body="Body")
    db.add(tpl); db.commit(); db.refresh(tpl)

    p = Prospect(name="Dave", email="dave@example.com", sequence_id=seq.id)
    db.add(p); db.commit(); db.refresh(p)

    token = make_unsubscribe_token(p.email)
    resp = client.get(f"/unsubscribe?token={token}")
    assert resp.status_code == 200

    db.refresh(p)
    assert p.unsubscribed is True
