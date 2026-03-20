# tests/test_analytics.py — analytics and sent-email endpoint tests

from datetime import datetime

from app.models import SentEmail


def _add_sent(db, status="sent"):
    e = SentEmail(
        to="a@b.com", subject="S", body="B",
        sent_at=datetime.utcnow(), status=status,
    )
    db.add(e); db.commit()


def test_analytics_empty(client):
    resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sent"] == 0
    assert data["total_failed"] == 0
    assert data["open_rate"] == 0


def test_analytics_counts_correctly(client, db):
    _add_sent(db, "sent")
    _add_sent(db, "sent")
    _add_sent(db, "failed")
    _add_sent(db, "opened")

    data = client.get("/analytics/summary").json()
    assert data["total_sent"] == 4
    assert data["total_failed"] == 1
    assert data["open_rate"] == 25.0


def test_sent_emails_list(client, db):
    _add_sent(db, "sent")
    _add_sent(db, "failed")
    resp = client.get("/sent-emails")
    assert resp.status_code == 200
    data = resp.json()
    # Paginated response: { items, total, page, per_page, pages }
    assert data["total"] == 2
    assert len(data["items"]) == 2
