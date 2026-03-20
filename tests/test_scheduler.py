# tests/test_scheduler.py — scheduler logic tests (via API endpoint)

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models import (
    Prospect, EmailTemplate, Sequence,
    ScheduledEmail, SentEmail,
)


def _seed(db: Session, unsubscribed: bool = False, send_at_offset_minutes: int = -10):
    """Seed one prospect + template + scheduled email. Returns (prospect, template, sched)."""
    seq = Sequence(name="Test Seq")
    db.add(seq); db.commit(); db.refresh(seq)

    tpl = EmailTemplate(name="T", subject="Hello {{name}}", body="<p>Hi {{name}}</p>")
    db.add(tpl); db.commit(); db.refresh(tpl)

    p = Prospect(name="Alice", email="alice@example.com", sequence_id=seq.id, unsubscribed=unsubscribed)
    db.add(p); db.commit(); db.refresh(p)

    sched = ScheduledEmail(
        prospect_id=p.id,
        template_id=tpl.id,
        sequence_id=seq.id,
        send_at=datetime.utcnow() + timedelta(minutes=send_at_offset_minutes),
        status="pending",
    )
    db.add(sched); db.commit(); db.refresh(sched)
    return p, tpl, sched


def test_scheduler_sends_pending_email(client, db):
    """Successful send: ScheduledEmail → sent, SentEmail created."""
    _seed(db)
    with patch("app.main.send_email", return_value="sent"), \
         patch("app.main._is_working", return_value="sent"):
        resp = client.post("/run-scheduler")
    assert resp.status_code == 200
    assert "processed 1" in resp.json()["message"]

    sched = db.exec(select(ScheduledEmail)).first()
    assert sched.status == "sent"
    sent_records = db.exec(select(SentEmail)).all()
    assert len(sent_records) == 1
    assert sent_records[0].status == "sent"


def test_scheduler_marks_failed_on_smtp_error(client, db):
    """SMTP failure: ScheduledEmail → failed, SentEmail created with failed status."""
    _seed(db)
    with patch("app.main.send_email", return_value="failed"), \
         patch("app.main._is_working", return_value="sent"):
        client.post("/run-scheduler")

    sched = db.exec(select(ScheduledEmail)).first()
    assert sched.status == "failed"
    sent_records = db.exec(select(SentEmail)).all()
    assert sent_records[0].status == "failed"


def test_scheduler_skips_unsubscribed_prospect(client, db):
    """Unsubscribed prospect: email NOT sent, sched marked failed."""
    _seed(db, unsubscribed=True)
    with patch("app.main.send_email") as mock_send, \
         patch("app.main._is_working", return_value="sent"):
        client.post("/run-scheduler")
        mock_send.assert_not_called()

    sched = db.exec(select(ScheduledEmail)).first()
    assert sched.status == "failed"


def test_scheduler_respects_send_window(client, db):
    """Outside send window: no emails sent."""
    _seed(db)
    with patch("app.main._is_working", return_value=False):
        resp = client.post("/run-scheduler")
    assert "outside window" in resp.json()["message"]

    sched = db.exec(select(ScheduledEmail)).first()
    assert sched.status == "pending"


def test_scheduler_respects_daily_limit(client, db):
    """Daily limit reached: no emails sent."""
    _seed(db)
    with patch("app.main._sent_today", return_value=9999), \
         patch("app.main._is_working", return_value="sent"):
        resp = client.post("/run-scheduler")
    assert "daily limit" in resp.json()["message"]


def test_force_scheduler_ignores_limits(client, db):
    """Force mode sends even outside working hours."""
    _seed(db)
    with patch("app.main.send_email", return_value="sent"), \
         patch("app.main._is_working", return_value=False):
        resp = client.post("/force-scheduler")
    assert "processed 1" in resp.json()["message"]


def test_scheduler_dedup_no_double_send(client, db):
    """Two consecutive scheduler calls only send the email once."""
    _seed(db)
    call_count = 0

    def fake_send(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return "sent"

    with patch("app.main.send_email", side_effect=fake_send), \
         patch("app.main._is_working", return_value="sent"):
        client.post("/run-scheduler")
        client.post("/run-scheduler")

    assert call_count == 1


def test_scheduler_future_emails_not_sent(client, db):
    """Email scheduled 1 hour in the future is not picked up."""
    _seed(db, send_at_offset_minutes=60)
    with patch("app.main.send_email") as mock_send, \
         patch("app.main._is_working", return_value="sent"):
        resp = client.post("/run-scheduler")
        mock_send.assert_not_called()
    assert "processed 0" in resp.json()["message"]


def test_tracking_pixel_id_passed_to_send_email(client, db):
    """The scheduler passes email_id to send_email for tracking pixel injection."""
    _seed(db)
    with patch("app.main.send_email", return_value="sent") as mock_send, \
         patch("app.main._is_working", return_value="sent"):
        client.post("/run-scheduler")
        call_kwargs = mock_send.call_args.kwargs
        assert "email_id" in call_kwargs
        assert call_kwargs["email_id"] is not None
