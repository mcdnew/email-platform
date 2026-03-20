# tests/test_crud.py — CRUD endpoint tests

from app.models import Prospect, EmailTemplate, Sequence, SequenceStep


# ── Prospects ──────────────────────────────────────────────────────────────────

def test_create_and_list_prospect(client):
    resp = client.post("/prospects", json={"name": "Alice", "email": "alice@x.com"})
    assert resp.status_code == 200
    resp = client.get("/prospects")
    assert resp.status_code == 200
    # Paginated response: { items, total, page, per_page, pages }
    assert any(p["email"] == "alice@x.com" for p in resp.json()["items"])


def test_delete_prospect(client):
    r = client.post("/prospects", json={"name": "Bob", "email": "bob@x.com"})
    pid = r.json()["id"]
    assert client.delete(f"/prospects/{pid}").status_code == 200
    prospects = client.get("/prospects").json()["items"]
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


# ── Bulk import ──────────────────────────────────────────────────────────────

def test_bulk_import_prospects(client):
    """POST /prospects/bulk accepts a JSON array and imports valid rows."""
    resp = client.post("/prospects/bulk", json=[
        {"name": "Alice", "email": "bulk_a@x.com"},
        {"name": "Bob",   "email": "bulk_b@x.com", "company": "Acme"},
    ])
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0
    assert data["errors"] == []

    items = client.get("/prospects").json()["items"]
    emails = [p["email"] for p in items]
    assert "bulk_a@x.com" in emails
    assert "bulk_b@x.com" in emails


def test_bulk_import_skips_duplicates(client):
    """Duplicate emails in a bulk import are counted as skipped, not errors."""
    client.post("/prospects", json={"name": "Alice", "email": "dup_bulk@x.com"})
    resp = client.post("/prospects/bulk", json=[
        {"name": "Alice Again", "email": "dup_bulk@x.com"},  # duplicate
    ])
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 0
    assert data["skipped"] == 1


# ── Pagination ────────────────────────────────────────────────────────────────

def test_prospects_pagination(client):
    """GET /prospects returns paginated shape with total/page/per_page/pages."""
    resp = client.get("/prospects?page=1&per_page=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert data["page"] == 1
    assert data["per_page"] == 10


def test_prospects_search(client):
    """GET /prospects?search= returns only matching rows."""
    client.post("/prospects", json={"name": "Searchable Prospect", "email": "search_unique@x.com"})
    resp = client.get("/prospects?search=search_unique")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(p["email"] == "search_unique@x.com" for p in data["items"])


def test_sequences_reorder(client):
    """POST /sequences/{sid}/reorder updates delay_days for each step."""
    t1 = client.post("/templates", json={"name": "T1", "subject": "S1", "body": "B"}).json()
    t2 = client.post("/templates", json={"name": "T2", "subject": "S2", "body": "B"}).json()
    s = client.post("/sequences", json={"name": "Reorder Test"}).json()
    s1 = client.post(f"/sequences/{s['id']}/steps", json={"sequence_id": s["id"], "template_id": t1["id"], "delay_days": 0}).json()
    s2 = client.post(f"/sequences/{s['id']}/steps", json={"sequence_id": s["id"], "template_id": t2["id"], "delay_days": 3}).json()

    # Reorder: swap delay_days
    resp = client.post(f"/sequences/{s['id']}/reorder", json={
        "steps": [{"step_id": s1["id"], "delay_days": 3}, {"step_id": s2["id"], "delay_days": 0}]
    })
    assert resp.status_code == 200

    steps = client.get(f"/sequences/{s['id']}/steps").json()
    step_map = {step["id"]: step["delay_days"] for step in steps}
    assert step_map[s1["id"]] == 3
    assert step_map[s2["id"]] == 0


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
