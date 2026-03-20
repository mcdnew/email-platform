# tests/test_endpoints.py — coverage for untested main.py endpoints

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models import (
    Prospect, EmailTemplate, Sequence, SequenceStep,
    ScheduledEmail, SentEmail, SmtpSettings,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_prospect(db, email="p@example.com", name="Alice", unsubscribed=False):
    p = Prospect(name=name, email=email, unsubscribed=unsubscribed)
    db.add(p); db.commit(); db.refresh(p)
    return p

def _make_template(db, name="T", subject="Hi", body="<p>body</p>"):
    t = EmailTemplate(name=name, subject=subject, body=body)
    db.add(t); db.commit(); db.refresh(t)
    return t

def _make_sequence(db, name="Seq"):
    s = Sequence(name=name)
    db.add(s); db.commit(); db.refresh(s)
    return s

def _make_step(db, seq_id, tpl_id, delay_days=0):
    step = SequenceStep(sequence_id=seq_id, template_id=tpl_id, delay_days=delay_days)
    db.add(step); db.commit(); db.refresh(step)
    return step

def _make_scheduled(db, prospect_id, template_id, sequence_id=None,
                    status="pending", offset_minutes=-10):
    s = ScheduledEmail(
        prospect_id=prospect_id,
        template_id=template_id,
        sequence_id=sequence_id,
        send_at=datetime.utcnow() + timedelta(minutes=offset_minutes),
        status=status,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s

def _make_sent(db, prospect_id, template_id, status="sent"):
    s = SentEmail(
        to="x@example.com",
        subject="S",
        body="B",
        sent_at=datetime.utcnow(),
        status=status,
        prospect_id=prospect_id,
        template_id=template_id,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


# ─── scheduled-email endpoints ──────────────────────────────────────────────

class TestScheduledEmailEndpoints:
    def test_list_scheduled(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        _make_scheduled(db, p.id, t.id)
        resp = client.get("/scheduled-emails")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["prospect_name"] == "Alice"
        assert items[0]["template_name"] == "T"

    def test_patch_schedule_send_at(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        s = _make_scheduled(db, p.id, t.id)
        new_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        resp = client.patch(f"/scheduled-emails/{s.id}", json={"send_at": new_time})
        assert resp.status_code == 200

    def test_patch_schedule_template_id(self, client, db):
        p = _make_prospect(db)
        t1 = _make_template(db, name="T1")
        t2 = _make_template(db, name="T2")
        s = _make_scheduled(db, p.id, t1.id)
        resp = client.patch(f"/scheduled-emails/{s.id}", json={"template_id": t2.id})
        assert resp.status_code == 200

    def test_patch_schedule_not_found(self, client, db):
        resp = client.patch("/scheduled-emails/999", json={"send_at": datetime.utcnow().isoformat()})
        assert resp.status_code == 404

    def test_patch_schedule_not_pending(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        s = _make_scheduled(db, p.id, t.id, status="sent")
        resp = client.patch(f"/scheduled-emails/{s.id}", json={"send_at": datetime.utcnow().isoformat()})
        assert resp.status_code == 409

    def test_patch_schedule_invalid_template(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        s = _make_scheduled(db, p.id, t.id)
        resp = client.patch(f"/scheduled-emails/{s.id}", json={"template_id": 9999})
        assert resp.status_code == 404

    def test_delete_schedule(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        s = _make_scheduled(db, p.id, t.id)
        resp = client.delete(f"/scheduled-emails/{s.id}")
        assert resp.status_code == 200
        # Verify deletion: patch now returns 404
        resp2 = client.patch(f"/scheduled-emails/{s.id}", json={"send_at": datetime.utcnow().isoformat()})
        assert resp2.status_code == 404

    def test_delete_schedule_not_found(self, client, db):
        resp = client.delete("/scheduled-emails/999")
        assert resp.status_code == 404

    def test_mark_sent(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        s = _make_scheduled(db, p.id, t.id)
        resp = client.post(f"/scheduled-emails/{s.id}/mark-sent")
        assert resp.status_code == 200
        db.refresh(s)
        assert s.status == "sent"

    def test_mark_sent_not_found(self, client, db):
        resp = client.post("/scheduled-emails/999/mark-sent")
        assert resp.status_code == 404


# ─── prospects CRUD & filters ────────────────────────────────────────────────

class TestProspectEndpoints:
    def test_add_prospect(self, client, db):
        resp = client.post("/prospects", json={"name": "Bob", "email": "bob@x.com"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "bob@x.com"

    def test_add_prospect_duplicate(self, client, db):
        client.post("/prospects", json={"name": "Bob", "email": "bob@x.com"})
        resp = client.post("/prospects", json={"name": "Bob", "email": "bob@x.com"})
        assert resp.status_code == 409

    def test_list_prospects_paginated(self, client, db):
        for i in range(5):
            _make_prospect(db, email=f"p{i}@x.com", name=f"P{i}")
        resp = client.get("/prospects?page=1&per_page=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["pages"] == 2

    def test_list_prospects_filter_assigned(self, client, db):
        seq = _make_sequence(db)
        p_assigned = Prospect(name="A", email="a@x.com", sequence_id=seq.id)
        p_unassigned = Prospect(name="B", email="b@x.com")
        db.add(p_assigned); db.add(p_unassigned); db.commit()

        resp = client.get("/prospects?assigned=true")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["sequence_id"] is not None for i in items)

        resp = client.get("/prospects?assigned=false")
        items = resp.json()["items"]
        assert all(i["sequence_id"] is None for i in items)

    def test_list_prospects_filter_unsubscribed(self, client, db):
        _make_prospect(db, email="sub@x.com", unsubscribed=False)
        _make_prospect(db, email="unsub@x.com", unsubscribed=True)

        resp = client.get("/prospects?unsubscribed=true")
        items = resp.json()["items"]
        assert all(i["unsubscribed"] for i in items)

        resp = client.get("/prospects?unsubscribed=false")
        items = resp.json()["items"]
        assert all(not i["unsubscribed"] for i in items)

    def test_list_prospects_search(self, client, db):
        _make_prospect(db, email="alice@x.com", name="Alice")
        _make_prospect(db, email="bob@x.com", name="Bob")
        resp = client.get("/prospects?search=alice")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Alice"

    def test_list_prospects_sort_desc(self, client, db):
        _make_prospect(db, email="a@x.com", name="Alpha")
        _make_prospect(db, email="z@x.com", name="Zeta")
        resp = client.get("/prospects?sort_by=name&order=desc")
        items = resp.json()["items"]
        assert items[0]["name"] == "Zeta"

    def test_edit_prospect(self, client, db):
        p = _make_prospect(db)
        resp = client.put(f"/prospects/{p.id}", json={
            "name": "Updated", "email": "updated@x.com",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_edit_prospect_clears_sequence_and_schedule(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        p = Prospect(name="P", email="p@x.com", sequence_id=seq.id)
        db.add(p); db.commit(); db.refresh(p)
        _make_scheduled(db, p.id, t.id, sequence_id=seq.id)

        resp = client.put(f"/prospects/{p.id}", json={
            "name": "P", "email": "p@x.com", "sequence_id": None,
        })
        assert resp.status_code == 200
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 0

    def test_edit_prospect_not_found(self, client, db):
        resp = client.put("/prospects/999", json={"name": "X", "email": "x@x.com"})
        assert resp.status_code == 404

    def test_delete_prospect(self, client, db):
        p = _make_prospect(db)
        resp = client.delete(f"/prospects/{p.id}")
        assert resp.status_code == 200
        # Verify deletion: second delete returns 404
        resp2 = client.delete(f"/prospects/{p.id}")
        assert resp2.status_code == 404

    def test_delete_prospect_not_found(self, client, db):
        resp = client.delete("/prospects/999")
        assert resp.status_code == 404

    def test_bulk_import(self, client, db):
        items = [
            {"name": "A", "email": "a@x.com"},
            {"name": "B", "email": "b@x.com"},
        ]
        resp = client.post("/prospects/bulk", json=items)
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0

    def test_bulk_import_skips_duplicate(self, client, db):
        _make_prospect(db, email="dup@x.com")
        resp = client.post("/prospects/bulk", json=[{"name": "Dup", "email": "dup@x.com"}])
        data = resp.json()
        assert data["skipped"] == 1
        assert data["imported"] == 0


# ─── sequences CRUD & steps ──────────────────────────────────────────────────

class TestSequenceEndpoints:
    def test_list_sequences(self, client, db):
        _make_sequence(db, "S1")
        _make_sequence(db, "S2")
        resp = client.get("/sequences")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_sequence(self, client, db):
        resp = client.post("/sequences", json={"name": "New Seq"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Seq"

    def test_update_sequence(self, client, db):
        seq = _make_sequence(db)
        resp = client.patch(f"/sequences/{seq.id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_sequence_not_found(self, client, db):
        resp = client.patch("/sequences/999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_sequence(self, client, db):
        seq = _make_sequence(db)
        resp = client.delete(f"/sequences/{seq.id}")
        assert resp.status_code == 200

    def test_delete_sequence_not_found(self, client, db):
        resp = client.delete("/sequences/999")
        assert resp.status_code == 404

    def test_delete_sequence_cascades_steps_and_emails(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        step = _make_step(db, seq.id, t.id)
        p = _make_prospect(db)
        sched = _make_scheduled(db, p.id, t.id, sequence_id=seq.id)

        resp = client.delete(f"/sequences/{seq.id}")
        assert resp.status_code == 200
        # Verify cascade: sequence now returns 404 on delete
        resp2 = client.delete(f"/sequences/{seq.id}")
        assert resp2.status_code == 404
        # Verify the scheduled email was purged
        scheds = client.get("/scheduled-emails").json()
        assert all(s["id"] != sched.id for s in scheds)

    def test_add_step(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        resp = client.post(f"/sequences/{seq.id}/steps", json={
            "sequence_id": seq.id, "template_id": t.id, "delay_days": 3
        })
        assert resp.status_code == 200

    def test_add_step_sequence_not_found(self, client, db):
        t = _make_template(db)
        resp = client.post("/sequences/999/steps", json={
            "sequence_id": 999, "template_id": t.id, "delay_days": 0
        })
        assert resp.status_code == 400

    def test_add_step_template_not_found(self, client, db):
        seq = _make_sequence(db)
        resp = client.post(f"/sequences/{seq.id}/steps", json={
            "sequence_id": seq.id, "template_id": 9999, "delay_days": 0
        })
        assert resp.status_code == 400

    def test_edit_step(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        step = _make_step(db, seq.id, t.id, delay_days=1)
        resp = client.patch(f"/sequences/steps/{step.id}", json={
            "sequence_id": seq.id, "template_id": t.id, "delay_days": 7
        })
        assert resp.status_code == 200
        assert resp.json()["delay_days"] == 7

    def test_edit_step_not_found(self, client, db):
        resp = client.patch("/sequences/steps/999", json={
            "sequence_id": 1, "template_id": 1, "delay_days": 0
        })
        assert resp.status_code == 404

    def test_delete_step(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        step = _make_step(db, seq.id, t.id)
        resp = client.delete(f"/sequences/steps/{step.id}")
        assert resp.status_code == 200

    def test_delete_step_not_found(self, client, db):
        resp = client.delete("/sequences/steps/999")
        assert resp.status_code == 404

    def test_reorder_steps(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        step = _make_step(db, seq.id, t.id, delay_days=0)
        resp = client.post(f"/sequences/{seq.id}/reorder", json={
            "steps": [{"step_id": step.id, "delay_days": 5}]
        })
        assert resp.status_code == 200
        db.refresh(step)
        assert step.delay_days == 5

    def test_reorder_steps_sequence_not_found(self, client, db):
        resp = client.post("/sequences/999/reorder", json={"steps": []})
        assert resp.status_code == 404

    def test_list_steps(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        _make_step(db, seq.id, t.id, delay_days=2)
        resp = client.get(f"/sequences/{seq.id}/steps")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ─── templates CRUD ─────────────────────────────────────────────────────────

class TestTemplateEndpoints:
    def test_list_templates(self, client, db):
        _make_template(db, "T1")
        _make_template(db, "T2")
        resp = client.get("/templates")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_template(self, client, db):
        resp = client.post("/templates", json={"name": "New", "subject": "Subj", "body": "B"})
        assert resp.status_code == 200

    def test_update_template(self, client, db):
        t = _make_template(db)
        resp = client.patch(f"/templates/{t.id}", json={"name": "New", "subject": "New Subj", "body": "B"})
        assert resp.status_code == 200

    def test_update_template_not_found(self, client, db):
        resp = client.patch("/templates/999", json={"name": "X", "subject": "X", "body": "X"})
        assert resp.status_code == 404

    def test_delete_template(self, client, db):
        t = _make_template(db)
        resp = client.delete(f"/templates/{t.id}")
        assert resp.status_code == 200

    def test_delete_template_not_found(self, client, db):
        resp = client.delete("/templates/999")
        assert resp.status_code == 404

    def test_delete_template_in_use_returns_400(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        _make_step(db, seq.id, t.id)
        resp = client.delete(f"/templates/{t.id}")
        assert resp.status_code == 400


# ─── sent-emails & analytics ─────────────────────────────────────────────────

class TestAnalyticsEndpoints:
    def test_list_sent_paginated(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        for _ in range(5):
            _make_sent(db, p.id, t.id)
        resp = client.get("/sent-emails?page=1&per_page=3")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_list_sent_status_filter(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        _make_sent(db, p.id, t.id, status="sent")
        _make_sent(db, p.id, t.id, status="failed")
        resp = client.get("/sent-emails?status_filter=failed")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "failed"

    def test_analytics_summary(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        _make_sent(db, p.id, t.id, status="sent")
        _make_sent(db, p.id, t.id, status="opened")
        resp = client.get("/analytics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sent"] == 2
        assert data["open_rate"] == 50.0

    def test_analytics_summary_empty(self, client, db):
        resp = client.get("/analytics/summary")
        assert resp.status_code == 200
        assert resp.json()["open_rate"] == 0

    def test_analytics_by_template(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db, name="Promo")
        _make_sent(db, p.id, t.id, status="sent")
        _make_sent(db, p.id, t.id, status="opened")
        resp = client.get("/analytics/by-template")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["name"] == "Promo"
        assert items[0]["open_rate"] == 50.0

    def test_analytics_by_template_skips_zero_sent(self, client, db):
        _make_template(db, name="Unused")
        resp = client.get("/analytics/by-template")
        assert resp.json() == []

    def test_analytics_by_sequence(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        seq = _make_sequence(db, "Newsletter")
        s = SentEmail(
            to="x@x.com", subject="S", body="B",
            sent_at=datetime.utcnow(), status="sent",
            prospect_id=p.id, template_id=t.id, sequence_id=seq.id,
        )
        db.add(s); db.commit()
        resp = client.get("/analytics/by-sequence")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["name"] == "Newsletter"

    def test_analytics_by_sequence_skips_zero_sent(self, client, db):
        _make_sequence(db, "Empty")
        resp = client.get("/analytics/by-sequence")
        assert resp.json() == []


# ─── assign-sequence ─────────────────────────────────────────────────────────

class TestAssignSequence:
    def test_assign_sequence(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        _make_step(db, seq.id, t.id, delay_days=0)
        p = _make_prospect(db)

        resp = client.post("/assign-sequence", json={
            "prospect_ids": [p.id],
            "sequence_id": seq.id,
        })
        assert resp.status_code == 200
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 1

    def test_assign_sequence_with_start_date(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        _make_step(db, seq.id, t.id)
        p = _make_prospect(db)

        resp = client.post("/assign-sequence", json={
            "prospect_ids": [p.id],
            "sequence_id": seq.id,
            "start_date": "2026-06-01",
        })
        assert resp.status_code == 200

    def test_assign_sequence_with_ventilate(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        _make_step(db, seq.id, t.id)
        prospects = [_make_prospect(db, email=f"p{i}@x.com") for i in range(4)]

        resp = client.post("/assign-sequence", json={
            "prospect_ids": [p.id for p in prospects],
            "sequence_id": seq.id,
            "ventilate_days": 3,
        })
        assert resp.status_code == 200


# ─── timeline ────────────────────────────────────────────────────────────────

class TestTimeline:
    def test_timeline_with_sequence(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        step = _make_step(db, seq.id, t.id, delay_days=0)
        p = Prospect(name="P", email="p@x.com", sequence_id=seq.id)
        db.add(p); db.commit(); db.refresh(p)
        _make_scheduled(db, p.id, t.id, sequence_id=seq.id)

        resp = client.get(f"/prospects/{p.id}/timeline")
        assert resp.status_code == 200
        tl = resp.json()
        assert len(tl) == 1
        assert tl[0]["step_number"] == 1

    def test_timeline_without_sequence(self, client, db):
        p = _make_prospect(db)
        t = _make_template(db)
        _make_scheduled(db, p.id, t.id)

        resp = client.get(f"/prospects/{p.id}/timeline")
        assert resp.status_code == 200
        tl = resp.json()
        assert len(tl) == 1
        assert tl[0]["step_number"] is None

    def test_timeline_not_found(self, client, db):
        resp = client.get("/prospects/999/timeline")
        assert resp.status_code == 404


# ─── SMTP settings ────────────────────────────────────────────────────────────

class TestSmtpSettings:
    def test_get_smtp_no_db_row_returns_env_defaults(self, client, db):
        resp = client.get("/settings/smtp")
        assert resp.status_code == 200
        assert resp.json()["source"] == "env"
        assert resp.json()["smtp_password"] == ""

    def test_update_smtp_creates_row(self, client, db):
        resp = client.put("/settings/smtp", json={
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "user@test.com",
            "smtp_password": "secret",
        })
        assert resp.status_code == 200
        row = db.get(SmtpSettings, 1)
        assert row is not None
        assert row.smtp_server == "smtp.test.com"

    def test_get_smtp_with_db_row(self, client, db):
        row = SmtpSettings(
            id=1, smtp_server="db.smtp.com", smtp_port=465,
            smtp_user="db@x.com", smtp_password="pass",
        )
        db.add(row); db.commit()
        resp = client.get("/settings/smtp")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "db"
        assert data["smtp_server"] == "db.smtp.com"
        assert data["smtp_password"] == ""  # never returned

    def test_update_smtp_updates_existing_row(self, client, db):
        row = SmtpSettings(id=1, smtp_server="old.com", smtp_port=25)
        db.add(row); db.commit()
        resp = client.put("/settings/smtp", json={"smtp_server": "new.com"})
        assert resp.status_code == 200
        db.refresh(row)
        assert row.smtp_server == "new.com"

    def test_update_smtp_empty_password_not_overwritten(self, client, db):
        client.put("/settings/smtp", json={"smtp_server": "s.com", "smtp_password": "original"})
        # Sending empty string should NOT wipe the password
        client.put("/settings/smtp", json={"smtp_password": ""})
        row = db.get(SmtpSettings, 1)
        assert row.smtp_password == "original"


# ─── send-test ───────────────────────────────────────────────────────────────

class TestSendTest:
    def test_send_test_success(self, client, db):
        with patch("app.main.send_email", return_value="sent"):
            resp = client.post("/send-test", json={
                "email": "t@x.com", "subject": "Test", "body": "<p>Hi</p>"
            })
        assert resp.status_code == 200

    def test_send_test_smtp_failure(self, client, db):
        with patch("app.main.send_email", return_value="failed"):
            resp = client.post("/send-test", json={
                "email": "t@x.com", "subject": "Test", "body": "<p>Hi</p>"
            })
        assert resp.status_code == 500

    def test_send_test_uses_db_smtp_settings(self, client, db):
        row = SmtpSettings(
            id=1, smtp_server="db.smtp.com", smtp_port=587,
            smtp_user="u@x.com", smtp_password="pw",
        )
        db.add(row); db.commit()

        captured = {}
        def fake_send(**kwargs):
            captured.update(kwargs)
            return "sent"

        with patch("app.main.send_email", side_effect=fake_send):
            client.post("/send-test", json={"email": "t@x.com", "subject": "S", "body": "B"})

        assert captured.get("smtp_override") is not None
        assert captured["smtp_override"]["smtp_server"] == "db.smtp.com"


# ─── scheduler: bounced & missing prospect edge cases ────────────────────────

class TestSchedulerEdgeCases:
    def test_scheduler_bounced_unsubscribes_prospect(self, client, db):
        seq = _make_sequence(db)
        t = _make_template(db)
        p = _make_prospect(db)
        _make_scheduled(db, p.id, t.id, sequence_id=seq.id)

        with patch("app.main.send_email", return_value="bounced"), \
             patch("app.main._is_working", return_value=True):
            client.post("/run-scheduler")

        db.refresh(p)
        assert p.unsubscribed is True

    def test_scheduler_missing_prospect_marks_failed(self, client, db):
        t = _make_template(db)
        # create scheduled email referencing a non-existent prospect
        s = ScheduledEmail(
            prospect_id=9999,
            template_id=t.id,
            send_at=datetime.utcnow() - timedelta(minutes=5),
            status="pending",
        )
        db.add(s); db.commit(); db.refresh(s)

        with patch("app.main._is_working", return_value=True):
            client.post("/run-scheduler")

        db.refresh(s)
        assert s.status == "failed"

    def test_scheduler_smtp_override_used_when_db_row_exists(self, client, db):
        smtp_row = SmtpSettings(
            id=1, smtp_server="override.smtp.com", smtp_port=587,
            smtp_user="u@x.com", smtp_password="pw",
        )
        db.add(smtp_row); db.commit()

        p = _make_prospect(db)
        t = _make_template(db)
        _make_scheduled(db, p.id, t.id)

        captured = {}
        def fake_send(**kwargs):
            captured.update(kwargs)
            return "sent"

        with patch("app.main.send_email", side_effect=fake_send), \
             patch("app.main._is_working", return_value=True):
            client.post("/run-scheduler")

        assert captured.get("smtp_override") is not None
        assert captured["smtp_override"]["smtp_server"] == "override.smtp.com"


# ─── error log & dev endpoints ───────────────────────────────────────────────

class TestDevEndpoints:
    def test_get_error_log_blocked_in_production(self, client, db):
        with patch.dict(os.environ, {"DEV_MODE": "false"}):
            resp = client.get("/error-log")
        assert resp.status_code == 403

    def test_get_error_log_returns_entries_in_dev(self, client, db, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text('{"event": "test_event"}\n')
        with patch.dict(os.environ, {"DEV_MODE": "true"}), \
             patch("app.main.settings") as mock_settings:
            mock_settings.API_KEY = ""
            mock_settings.LOG_PATH = str(log_file)
            resp = client.get("/error-log")
        assert resp.status_code == 200
        assert resp.json()["entries"][0]["event"] == "test_event"

    def test_get_error_log_no_file_returns_empty(self, client, db):
        with patch.dict(os.environ, {"DEV_MODE": "true"}), \
             patch("app.main.settings") as mock_settings:
            mock_settings.API_KEY = ""
            mock_settings.LOG_PATH = "/nonexistent/path.log"
            resp = client.get("/error-log")
        assert resp.status_code == 200
        assert resp.json()["entries"] == []

    def test_clear_error_log_blocked_in_production(self, client, db):
        with patch.dict(os.environ, {"DEV_MODE": "false"}):
            resp = client.post("/clear-error-log")
        assert resp.status_code == 403

    def test_clear_error_log_in_dev(self, client, db, tmp_path):
        log_file = tmp_path / "err.log"
        log_file.write_text("some content\n")
        with patch.dict(os.environ, {"DEV_MODE": "true"}), \
             patch("app.main.settings") as mock_settings:
            mock_settings.API_KEY = ""
            mock_settings.LOG_PATH = str(log_file)
            resp = client.post("/clear-error-log")
        assert resp.status_code == 200
        assert log_file.read_text() == ""

    def test_cron_log_not_found(self, client, db):
        resp = client.get("/cron-log")
        assert resp.status_code == 404

    def test_reset_all_blocked_in_production(self, client, db):
        with patch.dict(os.environ, {"DEV_MODE": "false"}):
            resp = client.post("/reset-all")
        assert resp.status_code == 403

    def test_reset_all_in_dev(self, client, db):
        _make_prospect(db)
        _make_template(db)
        with patch.dict(os.environ, {"DEV_MODE": "true"}):
            resp = client.post("/reset-all")
        assert resp.status_code == 200
        from app.models import Prospect as P
        assert db.exec(select(P)).all() == []
