# tests/test_tracking.py — open tracking pixel tests

from datetime import datetime

from app.models import SentEmail


def _make_sent_email(db, status="sent"):
    e = SentEmail(
        to="a@b.com", subject="Hi", body="<p>test</p>",
        sent_at=datetime.utcnow(), status=status,
    )
    db.add(e); db.commit(); db.refresh(e)
    return e


def test_track_open_flips_status_to_opened(client, db):
    """GET /track_open returns a pixel and flips status sent → opened."""
    e = _make_sent_email(db, status="sent")
    resp = client.get(f"/track_open?email_id={e.id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/gif"

    db.refresh(e)
    assert e.status == "opened"


def test_track_open_idempotent(client, db):
    """Calling /track_open twice doesn't break anything (already opened stays opened)."""
    e = _make_sent_email(db, status="sent")
    client.get(f"/track_open?email_id={e.id}")
    client.get(f"/track_open?email_id={e.id}")

    db.refresh(e)
    assert e.status == "opened"


def test_track_open_invalid_id_returns_404(client, db):
    """Unknown email_id returns 404."""
    resp = client.get("/track_open?email_id=99999")
    assert resp.status_code == 404
