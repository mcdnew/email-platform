"""CRUD helpers for email-platform – SQLAlchemy 2.x compatible."""

from __future__ import annotations
import random
from datetime import datetime, timedelta, date, time
from typing import List

from sqlmodel import Session, select
from sqlalchemy import func, delete

from app.models import (
    Prospect,
    EmailTemplate,
    Sequence,
    SequenceStep,
    ScheduledEmail,
    SentEmail,
    EmailTemplateUpdate,
)
from app.config import settings

# ─────────────────────────────── helpers ───────────────────────────────
def _next_working(d: date) -> date:
    """Return next weekday ≥ d (skipping Sat/Sun)."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d

def _random_times(base: date, n: int, start_h: int = 9, end_h: int = 21) -> list[datetime]:
    """Return n unique datetimes between start_h and end_h on date base."""
    minutes = (end_h - start_h) * 60
    if n > minutes:
        raise ValueError("window too small")
    picks = random.sample(range(minutes), n)
    return [
        datetime.combine(base, time(start_h)) + timedelta(minutes=m)
        for m in sorted(picks)
    ]

def _already_scheduled(session: Session, d: date) -> int:
    """Count how many ScheduledEmail have send_at on calendar-day d."""
    start = datetime.combine(d, time.min)
    end   = datetime.combine(d, time.max)
    return session.exec(
        select(func.count()).select_from(ScheduledEmail)
        .where(
            ScheduledEmail.send_at >= start,
            ScheduledEmail.send_at <= end
        )
    ).scalar_one()  # COUNT(*) always returns exactly one row

# ───────────────────────── Prospect CRUD ───────────────────────────────
def create_prospect(session: Session, p: Prospect) -> Prospect:
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

def get_prospects(session: Session) -> list[Prospect]:
    return session.exec(select(Prospect)).all()

def update_prospect(session: Session, p: Prospect) -> Prospect:
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

def delete_prospect(session: Session, pid: int) -> bool:
    """Delete prospect and any related ScheduledEmail and SentEmail rows."""
    prospect = session.get(Prospect, pid)
    if not prospect:
        return False
    # bulk-delete their schedules and sent records
    session.exec(delete(ScheduledEmail).where(ScheduledEmail.prospect_id == pid))
    session.exec(delete(SentEmail).where(SentEmail.prospect_id == pid))
    session.delete(prospect)
    session.commit()
    return True

# ───────────────────────── Template CRUD ───────────────────────────────
def create_template(session: Session, t: EmailTemplate) -> EmailTemplate:
    session.add(t)
    session.commit()
    session.refresh(t)
    return t

def get_templates(session: Session) -> list[EmailTemplate]:
    return session.exec(select(EmailTemplate)).all()

def update_template(session: Session, tid: int, up: EmailTemplateUpdate) -> EmailTemplate | None:
    tpl = session.get(EmailTemplate, tid)
    if not tpl:
        return None
    for k, v in up.dict(exclude_unset=True).items():
        setattr(tpl, k, v)
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl

def delete_template(session: Session, tid: int) -> bool | None:
    """Return None if in use, False if not found, True if deleted."""
    in_use = session.exec(
        select(SequenceStep).where(SequenceStep.template_id == tid)
    ).first()
    if in_use:
        return None
    tpl = session.get(EmailTemplate, tid)
    if not tpl:
        return False
    session.delete(tpl)
    session.commit()
    return True

# ─────────────────────── Sequence & Steps CRUD ────────────────────────
def create_sequence(session: Session, seq: Sequence) -> Sequence:
    session.add(seq)
    session.commit()
    session.refresh(seq)
    return seq

def get_sequences(session: Session) -> list[Sequence]:
    return session.exec(select(Sequence)).all()

def create_sequence_step(session: Session, step: SequenceStep) -> SequenceStep:
    session.add(step)
    session.commit()
    session.refresh(step)
    return step

def get_sequence_steps(session: Session, seq_id: int) -> list[SequenceStep]:
    return session.exec(
        select(SequenceStep).where(SequenceStep.sequence_id == seq_id)
    ).all()

def update_sequence_step(session: Session, sid: int, up: SequenceStep) -> SequenceStep | None:
    step = session.get(SequenceStep, sid)
    if not step:
        return None
    for k, v in up.dict(exclude_unset=True).items():
        setattr(step, k, v)
    session.add(step)
    session.commit()
    session.refresh(step)
    return step

def delete_sequence_step(session: Session, sid: int) -> bool:
    step = session.get(SequenceStep, sid)
    if not step:
        return False
    session.delete(step)
    session.commit()
    return True

# ─────────────────────── Bulk scheduling ──────────────────────────────# ─────────────────────── Bulk scheduling ──────────────────────────────
def bulk_assign_sequence_to_prospects(
    session: Session,
    prospect_ids: List[int],
    sequence_id: int,
    ventilate_days: int = 0,
    start_date: date | None = None,
):
    """
    Assign *sequence_id* to each prospect in *prospect_ids* and create
    corresponding ScheduledEmail rows, spreading first step over ventilate_days.
    """
    if start_date is None:
        start_date = date.today()

    # fetch all steps once
    steps = session.exec(
        select(SequenceStep).where(SequenceStep.sequence_id == sequence_id)
    ).all()
    if not steps:
        return

    # random offsets for day-0 send
    offsets = (
        [0] * len(prospect_ids)
        if ventilate_days == 0
        else [random.randint(0, ventilate_days - 1) for _ in prospect_ids]
    )
    first_dates = [start_date + timedelta(days=o) for o in offsets]

    for pid, first_d in zip(prospect_ids, first_dates):
        prospect = session.get(Prospect, pid)
        if not prospect:
            continue

        # attach sequence
        prospect.sequence_id = sequence_id
        session.add(prospect)

        # purge any old schedule
        session.exec(delete(ScheduledEmail).where(ScheduledEmail.prospect_id == pid))

        # schedule each step
        for step in steps:
            send_day = _next_working(first_d + timedelta(days=step.delay_days))
            send_dt = _random_times(send_day, 1)[0]

            # prevent scheduling in the past
            now = datetime.now()
            if send_day == now.date() and send_dt < now:
                send_dt = now + timedelta(minutes=30)

            sched = ScheduledEmail(
                prospect_id=pid,
                sequence_id=sequence_id,
                template_id=step.template_id,
                send_at=send_dt,
                status="pending",
            )
            session.add(sched)

    session.commit()

