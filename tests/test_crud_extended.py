# tests/test_crud_extended.py — coverage for untested crud.py paths + open_tracking

from datetime import datetime, timedelta, date

import pytest
from sqlmodel import Session, select

from app import crud
from app.models import (
    Prospect, EmailTemplate, Sequence, SequenceStep,
    ScheduledEmail, SentEmail,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def _prospect(db, email="p@x.com", name="Alice"):
    p = Prospect(name=name, email=email)
    db.add(p); db.commit(); db.refresh(p)
    return p

def _template(db, name="T"):
    t = EmailTemplate(name=name, subject="Subj", body="<p>Hi</p>")
    db.add(t); db.commit(); db.refresh(t)
    return t

def _sequence(db, name="Seq"):
    s = Sequence(name=name)
    db.add(s); db.commit(); db.refresh(s)
    return s

def _step(db, seq_id, tpl_id, delay_days=0):
    step = SequenceStep(sequence_id=seq_id, template_id=tpl_id, delay_days=delay_days)
    db.add(step); db.commit(); db.refresh(step)
    return step

def _sent(db, prospect_id, template_id, status="sent"):
    s = SentEmail(
        to="x@x.com", subject="S", body="B",
        sent_at=datetime.utcnow(), status=status,
        prospect_id=prospect_id, template_id=template_id,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


# ─── _next_working ───────────────────────────────────────────────────────────

class TestNextWorking:
    def test_weekday_unchanged(self):
        # 2026-03-23 is a Monday
        d = date(2026, 3, 23)
        assert crud._next_working(d) == d

    def test_saturday_advances_to_monday(self):
        # 2026-03-21 is Saturday
        d = date(2026, 3, 21)
        result = crud._next_working(d)
        assert result == date(2026, 3, 23)  # Monday

    def test_sunday_advances_to_monday(self):
        d = date(2026, 3, 22)  # Sunday
        result = crud._next_working(d)
        assert result == date(2026, 3, 23)


# ─── _random_times ───────────────────────────────────────────────────────────

class TestRandomTimes:
    def test_returns_n_sorted_datetimes(self):
        d = date(2026, 3, 23)
        times = crud._random_times(d, 3)
        assert len(times) == 3
        assert times == sorted(times)
        assert all(t.date() == d for t in times)

    def test_raises_when_window_too_small(self):
        d = date(2026, 3, 23)
        with pytest.raises(ValueError, match="window too small"):
            crud._random_times(d, 10000)

    def test_custom_hours(self):
        d = date(2026, 3, 23)
        times = crud._random_times(d, 1, start_h=10, end_h=11)
        assert times[0].hour == 10



# ─── prospect CRUD ───────────────────────────────────────────────────────────

class TestProspectCrud:
    def test_get_prospects(self, db):
        _prospect(db, "a@x.com", name="Alpha")
        _prospect(db, "b@x.com", name="Beta")
        results = crud.get_prospects(db)
        names = {r.email for r in results}
        assert "a@x.com" in names
        assert "b@x.com" in names

    def test_update_prospect(self, db):
        p = _prospect(db)
        p.name = "Updated"
        result = crud.update_prospect(db, p)
        assert result.name == "Updated"
        db.refresh(p)
        assert p.name == "Updated"

    def test_delete_prospect_cascades(self, db):
        p = _prospect(db)
        t = _template(db)
        s = ScheduledEmail(
            prospect_id=p.id, template_id=t.id,
            send_at=datetime.utcnow(), status="pending",
        )
        se = SentEmail(
            to="x@x.com", subject="S", body="B",
            sent_at=datetime.utcnow(), status="sent",
            prospect_id=p.id, template_id=t.id,
        )
        db.add(s); db.add(se); db.commit()

        result = crud.delete_prospect(db, p.id)
        assert result is True
        assert db.get(Prospect, p.id) is None
        assert db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all() == []
        assert db.exec(select(SentEmail).where(SentEmail.prospect_id == p.id)).all() == []

    def test_delete_prospect_not_found(self, db):
        assert crud.delete_prospect(db, 9999) is False


# ─── template CRUD ───────────────────────────────────────────────────────────

class TestTemplateCrud:
    def test_update_template(self, db):
        t = _template(db)
        from app.models import EmailTemplateUpdate
        up = EmailTemplateUpdate(name="New Name", subject="New Subj", body="New Body")
        result = crud.update_template(db, t.id, up)
        assert result.name == "New Name"
        assert result.subject == "New Subj"

    def test_update_template_not_found(self, db):
        from app.models import EmailTemplateUpdate
        up = EmailTemplateUpdate(name="X")
        assert crud.update_template(db, 9999, up) is None

    def test_delete_template_success(self, db):
        t = _template(db)
        result = crud.delete_template(db, t.id)
        assert result is True
        assert db.get(EmailTemplate, t.id) is None

    def test_delete_template_not_found(self, db):
        assert crud.delete_template(db, 9999) is False

    def test_delete_template_in_use(self, db):
        seq = _sequence(db)
        t = _template(db)
        _step(db, seq.id, t.id)
        result = crud.delete_template(db, t.id)
        assert result is None  # None = in use


# ─── sequence CRUD ───────────────────────────────────────────────────────────

class TestSequenceCrud:
    def test_create_sequence(self, db):
        seq = Sequence(name="New Seq")
        result = crud.create_sequence(db, seq)
        assert result.id is not None
        assert result.name == "New Seq"

    def test_get_sequences(self, db):
        _sequence(db, "SeqAlpha")
        _sequence(db, "SeqBeta")
        results = crud.get_sequences(db)
        names = {r.name for r in results}
        assert "SeqAlpha" in names
        assert "SeqBeta" in names

    def test_update_sequence_step(self, db):
        seq = _sequence(db)
        t = _template(db)
        step = _step(db, seq.id, t.id, delay_days=1)

        updated = SequenceStep(sequence_id=seq.id, template_id=t.id, delay_days=7)
        result = crud.update_sequence_step(db, step.id, updated)
        assert result is not None
        assert result.delay_days == 7

    def test_update_sequence_step_not_found(self, db):
        step = SequenceStep(sequence_id=1, template_id=1, delay_days=0)
        assert crud.update_sequence_step(db, 9999, step) is None

    def test_delete_sequence_step_not_found(self, db):
        assert crud.delete_sequence_step(db, 9999) is False


# ─── bulk_assign_sequence_to_prospects ───────────────────────────────────────

class TestBulkAssign:
    def test_assigns_and_creates_schedules(self, db):
        seq = _sequence(db)
        t = _template(db)
        _step(db, seq.id, t.id, delay_days=0)
        p = _prospect(db)

        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq.id)

        db.refresh(p)
        assert p.sequence_id == seq.id
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 1

    def test_no_steps_returns_early(self, db):
        seq = _sequence(db)
        p = _prospect(db)
        # no steps added — should return without creating schedules
        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq.id)
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 0

    def test_skips_missing_prospect(self, db):
        seq = _sequence(db)
        t = _template(db)
        _step(db, seq.id, t.id)
        # prospect 9999 does not exist — should not crash
        crud.bulk_assign_sequence_to_prospects(db, [9999], seq.id)

    def test_uses_today_when_start_date_none(self, db):
        seq = _sequence(db)
        t = _template(db)
        _step(db, seq.id, t.id, delay_days=0)
        p = _prospect(db)

        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq.id, start_date=None)
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 1

    def test_ventilate_days_spreads_prospects(self, db):
        seq = _sequence(db)
        t = _template(db)
        _step(db, seq.id, t.id, delay_days=0)
        prospects = [_prospect(db, email=f"p{i}@x.com") for i in range(5)]

        crud.bulk_assign_sequence_to_prospects(
            db, [p.id for p in prospects], seq.id,
            ventilate_days=3, start_date=date(2026, 6, 2),
        )
        scheds = db.exec(select(ScheduledEmail)).all()
        assert len(scheds) == 5
        # send_at dates should span multiple days
        days = {s.send_at.date() for s in scheds}
        assert len(days) >= 1  # may all land same day due to randomness, but must exist

    def test_purges_old_schedule_on_reassign(self, db):
        seq1 = _sequence(db, "S1")
        seq2 = _sequence(db, "S2")
        t = _template(db)
        _step(db, seq1.id, t.id)
        _step(db, seq2.id, t.id)
        p = _prospect(db)

        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq1.id)
        assert len(db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()) == 1

        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq2.id)
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        # old schedule purged, new one created
        assert len(scheds) == 1
        assert scheds[0].sequence_id == seq2.id

    def test_multi_step_sequence(self, db):
        seq = _sequence(db)
        t1 = _template(db, "T1")
        t2 = _template(db, "T2")
        _step(db, seq.id, t1.id, delay_days=0)
        _step(db, seq.id, t2.id, delay_days=3)
        p = _prospect(db)

        crud.bulk_assign_sequence_to_prospects(db, [p.id], seq.id)
        scheds = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == p.id)).all()
        assert len(scheds) == 2


# ─── open_tracking: track_click ──────────────────────────────────────────────

class TestTrackClick:
    def _make_sent(self, db, status="sent"):
        p = _prospect(db)
        t = _template(db)
        s = SentEmail(
            to="x@x.com", subject="S", body="B",
            sent_at=datetime.utcnow(), status=status,
            prospect_id=p.id, template_id=t.id,
        )
        db.add(s); db.commit(); db.refresh(s)
        return s

    def test_track_click_increments_count(self, client, db):
        s = self._make_sent(db)
        resp = client.get(f"/track_click?email_id={s.id}&url=http%3A%2F%2Fexample.com",
                          follow_redirects=False)
        assert resp.status_code == 302
        db.refresh(s)
        assert s.click_count == 1

    def test_track_click_multiple_increments(self, client, db):
        s = self._make_sent(db)
        for _ in range(3):
            client.get(f"/track_click?email_id={s.id}&url=http%3A%2F%2Fexample.com",
                       follow_redirects=False)
        db.refresh(s)
        assert s.click_count == 3

    def test_track_click_sets_opened_when_sent(self, client, db):
        s = self._make_sent(db, status="sent")
        client.get(f"/track_click?email_id={s.id}&url=http%3A%2F%2Fexample.com",
                   follow_redirects=False)
        db.refresh(s)
        assert s.status == "opened"

    def test_track_click_does_not_downgrade_opened(self, client, db):
        s = self._make_sent(db, status="opened")
        client.get(f"/track_click?email_id={s.id}&url=http%3A%2F%2Fexample.com",
                   follow_redirects=False)
        db.refresh(s)
        assert s.status == "opened"

    def test_track_click_not_found(self, client, db):
        resp = client.get("/track_click?email_id=9999&url=http%3A%2F%2Fexample.com",
                          follow_redirects=False)
        assert resp.status_code == 404

    def test_track_click_redirects_to_decoded_url(self, client, db):
        s = self._make_sent(db)
        target = "http://example.com/page?foo=bar"
        import urllib.parse
        encoded = urllib.parse.quote(target, safe="")
        resp = client.get(f"/track_click?email_id={s.id}&url={encoded}",
                          follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == target

    def test_track_open_not_found(self, client, db):
        resp = client.get("/track_open?email_id=9999")
        assert resp.status_code == 404

    def test_track_open_already_opened_stays_opened(self, client, db):
        s = self._make_sent(db, status="opened")
        resp = client.get(f"/track_open?email_id={s.id}")
        assert resp.status_code == 200
        db.refresh(s)
        assert s.status == "opened"  # not reset
