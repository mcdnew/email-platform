# tests/test_unsubscribe.py — unsubscribe endpoint and token tests

from datetime import datetime, timedelta
from sqlmodel import select

from app.models import Prospect, ScheduledEmail, EmailTemplate, Sequence
from app.tracking import make_unsubscribe_token, load_unsubscribe_token


def _seed_prospect_with_pending(db):
    seq = Sequence(name="S")
    db.add(seq); db.commit(); db.refresh(seq)

    tpl = EmailTemplate(name="T", subject="Hi", body="Body")
    db.add(tpl); db.commit(); db.refresh(tpl)

    p = Prospect(name="Bob", email="bob@example.com", sequence_id=seq.id)
    db.add(p); db.commit(); db.refresh(p)

    for _ in range(2):
        sched = ScheduledEmail(
            prospect_id=p.id,
            template_id=tpl.id,
            sequence_id=seq.id,
            send_at=datetime.utcnow() + timedelta(days=1),
            status="pending",
        )
        db.add(sched)
    db.commit()
    return p


def test_unsubscribe_valid_token_sets_flag(client, db):
    """Valid token marks prospect as unsubscribed."""
    p = _seed_prospect_with_pending(db)
    token = make_unsubscribe_token(p.email)

    resp = client.get(f"/unsubscribe?token={token}")
    assert resp.status_code == 200
    assert "unsubscribed" in resp.text.lower()

    db.refresh(p)
    assert p.unsubscribed is True


def test_unsubscribe_purges_pending_emails(client, db):
    """Unsubscribing deletes all pending ScheduledEmail rows for that prospect."""
    p = _seed_prospect_with_pending(db)
    token = make_unsubscribe_token(p.email)
    client.get(f"/unsubscribe?token={token}")

    remaining = db.exec(
        select(ScheduledEmail).where(
            ScheduledEmail.prospect_id == p.id,
            ScheduledEmail.status == "pending",
        )
    ).all()
    assert len(remaining) == 0


def test_unsubscribe_invalid_token_returns_400(client):
    """Tampered token returns 400 without crashing."""
    resp = client.get("/unsubscribe?token=notavalidtoken")
    assert resp.status_code == 400


def test_unsubscribe_unknown_email_graceful(client, db):
    """Valid token for non-existent email returns 200 (graceful no-op)."""
    token = make_unsubscribe_token("ghost@nowhere.com")
    resp = client.get(f"/unsubscribe?token={token}")
    assert resp.status_code == 200


def test_load_unsubscribe_token_roundtrip():
    """make → load roundtrip returns original email."""
    email = "test@example.com"
    token = make_unsubscribe_token(email)
    assert load_unsubscribe_token(token) == email


def test_load_unsubscribe_token_bad_input():
    """Invalid token returns None, no exception."""
    assert load_unsubscribe_token("garbage") is None
