# tests/test_crud.py — CRUD endpoint tests

from app.models import Prospect, EmailTemplate, Sequence, SequenceStep


# ── Prospects ──────────────────────────────────────────────────────────────────

def test_create_and_list_prospect(client):
    resp = client.post("/prospects", json={"name": "Alice", "email": "alice@x.com"})
    assert resp.status_code == 200
    resp = client.get("/prospects")
    assert resp.status_code == 200
    assert any(p["email"] == "alice@x.com" for p in resp.json())


def test_delete_prospect(client):
    r = client.post("/prospects", json={"name": "Bob", "email": "bob@x.com"})
    pid = r.json()["id"]
    assert client.delete(f"/prospects/{pid}").status_code == 200
    prospects = client.get("/prospects").json()
    assert not any(p["id"] == pid for p in prospects)


def test_delete_prospect_not_found(client):
    assert client.delete("/prospects/9999").status_code == 404


def test_duplicate_email_rejected(client):
    """Two prospects with the same email should not both be created (unique constraint)."""
    client.post("/prospects", json={"name": "Alice", "email": "dup@x.com"})
    resp = client.post("/prospects", json={"name": "Alice2", "email": "dup@x.com"})
    # Should fail with 4xx or 5xx (constraint violation)
    assert resp.status_code >= 400


# ── Templates ─────────────────────────────────────────────────────────────────

def test_create_and_list_template(client):
    resp = client.post("/templates", json={"name": "T", "subject": "Hi", "body": "<p>Hi</p>"})
    assert resp.status_code == 200
    assert any(t["name"] == "T" for t in client.get("/templates").json())


def test_delete_template_not_in_sequence(client):
    r = client.post("/templates", json={"name": "T", "subject": "Hi", "body": "Body"})
    tid = r.json()["id"]
    assert client.delete(f"/templates/{tid}").status_code == 200


def test_delete_template_blocked_when_in_sequence(client):
    """Template used in a sequence step cannot be deleted."""
    t = client.post("/templates", json={"name": "T", "subject": "Hi", "body": "Body"}).json()
    s = client.post("/sequences", json={"name": "S"}).json()
    client.post(f"/sequences/{s['id']}/steps", json={
        "sequence_id": s["id"], "template_id": t["id"], "delay_days": 0
    })
    resp = client.delete(f"/templates/{t['id']}")
    assert resp.status_code == 400


# ── Sequences ─────────────────────────────────────────────────────────────────

def test_create_and_list_sequence(client):
    r = client.post("/sequences", json={"name": "Seq1"})
    assert r.status_code == 200
    seqs = client.get("/sequences").json()
    assert any(s["name"] == "Seq1" for s in seqs)


def test_delete_sequence_cascades(client):
    """Deleting a sequence also removes its steps and scheduled emails."""
    from datetime import datetime
    t = client.post("/templates", json={"name": "T", "subject": "Hi", "body": "B"}).json()
    s = client.post("/sequences", json={"name": "S"}).json()
    client.post(f"/sequences/{s['id']}/steps", json={
        "sequence_id": s["id"], "template_id": t["id"], "delay_days": 0
    })

    # Create a prospect and assign the sequence
    p = client.post("/prospects", json={"name": "Z", "email": "z@x.com"}).json()
    client.post("/assign-sequence", json={"prospect_ids": [p["id"]], "sequence_id": s["id"]})

    # Delete the sequence
    assert client.delete(f"/sequences/{s['id']}").status_code == 200

    # Steps are gone
    steps = client.get(f"/sequences/{s['id']}/steps").json()
    assert steps == [] or client.get(f"/sequences/{s['id']}/steps").status_code == 404

    # Scheduled emails are gone
    scheduled = client.get("/scheduled-emails").json()
    assert not any(e["prospect_id"] == p["id"] for e in scheduled)


# ── Assign sequence ───────────────────────────────────────────────────────────

def test_assign_sequence_creates_scheduled_emails(client):
    t = client.post("/templates", json={"name": "T", "subject": "Hi", "body": "B"}).json()
    s = client.post("/sequences", json={"name": "S"}).json()
    client.post(f"/sequences/{s['id']}/steps", json={
        "sequence_id": s["id"], "template_id": t["id"], "delay_days": 0
    })
    p = client.post("/prospects", json={"name": "A", "email": "a@x.com"}).json()

    resp = client.post("/assign-sequence", json={"prospect_ids": [p["id"]], "sequence_id": s["id"]})
    assert resp.status_code == 200

    scheduled = client.get("/scheduled-emails").json()
    assert any(e["prospect_id"] == p["id"] for e in scheduled)
