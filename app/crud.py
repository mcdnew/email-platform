"""CRUD helpers for email-platform.

Implements bulk assignment with globally distributed scheduling as well as
standard CRUD operations for Prospects, Templates, Sequences and Steps.

This version fixes ScalarResult `.count()`/`.scalar_one()` errors by performing
pure SQL `COUNT(*)` queries via SQLAlchemy's `func.count()` which is safe and
efficient for large datasets.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, time
from typing import Sequence as _SeqType, List

from sqlmodel import Session, select, delete
from sqlalchemy import func

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


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #


def _rows_to_dict(rows: _SeqType) -> list[dict]:
    """Convert an iterator of SQLModel rows to plain dicts.

    Works both with ORM objects (have ``dict()``) and row tuples.
    """
    out: list[dict] = []
    for r in rows:
        if hasattr(r, "dict"):
            out.append(r.dict())
        elif hasattr(r, "_mapping"):  # SQLAlchemy Row
            out.append(dict(r._mapping))
        else:
            # Fallback: try vars()
            try:
                out.append(vars(r))
            except Exception:
                continue
    return out


def _get_next_working_day(dt: datetime.date):
    """Return first weekday >= *dt* (Mon-Fri)."""
    while dt.weekday() >= 5:
        dt += timedelta(days=1)
    return dt


def _random_times_for_window(
    base_date: datetime.date,
    count: int,
    start_hour: int = 9,
    end_hour: int = 21,
) -> list[datetime]:
    """Return *count* unique datetimes randomly spread inside the window."""
    window_minutes = (end_hour - start_hour) * 60
    if count > window_minutes:
        raise ValueError("More emails than available slots in the window")
    slots = random.sample(range(window_minutes), count)
    return [
        datetime.combine(base_date, time(start_hour, 0)) + timedelta(minutes=m)
        for m in sorted(slots)
    ]


# --------------------------------------------------------------------------- #
# Prospect CRUD
# --------------------------------------------------------------------------- #


def create_prospect(session: Session, prospect: Prospect):
    session.add(prospect)
    session.commit()
    session.refresh(prospect)
    return prospect


def get_prospects(session: Session):
    return session.exec(select(Prospect)).all()


def update_prospect(session: Session, prospect: Prospect):
    session.add(prospect)
    session.commit()
    session.refresh(prospect)
    return prospect


def delete_prospect(session: Session, prospect_id: int):
    prospect = session.get(Prospect, prospect_id)
    if not prospect:
        return False

    # Cascade-delete all scheduled & sent emails for this prospect
    session.exec(
        delete(ScheduledEmail).where(ScheduledEmail.prospect_id == prospect_id)
    )
    session.exec(
        delete(SentEmail).where(SentEmail.prospect_id == prospect_id)
    )

    session.delete(prospect)
    session.commit()
    return True


# --------------------------------------------------------------------------- #
# Template CRUD
# --------------------------------------------------------------------------- #


def create_template(session: Session, template: EmailTemplate):
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def get_templates(session: Session):
    return session.exec(select(EmailTemplate)).all()


def update_template(session: Session, template_id: int, data: EmailTemplateUpdate):
    tpl = session.get(EmailTemplate, template_id)
    if not tpl:
        return None
    for k, v in data.dict(exclude_unset=True).items():
        setattr(tpl, k, v)
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


def delete_template(session: Session, template_id: int):
    tpl = session.get(EmailTemplate, template_id)
    if not tpl:
        return False
    in_use = session.exec(
        select(SequenceStep).where(SequenceStep.template_id == template_id)
    ).first()
    if in_use:
        return None
    session.delete(tpl)
    session.commit()
    return True


# --------------------------------------------------------------------------- #
# Sequence + Steps CRUD
# --------------------------------------------------------------------------- #


def create_sequence(session: Session, sequence: Sequence):
    session.add(sequence)
    session.commit()
    session.refresh(sequence)
    return sequence


def get_sequences(session: Session):
    return session.exec(select(Sequence)).all()


def create_sequence_step(session: Session, step: SequenceStep):
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def get_sequence_steps(session: Session, sequence_id: int):
    return session.exec(
        select(SequenceStep).where(SequenceStep.sequence_id == sequence_id)
    ).all()


def update_sequence_step(session: Session, step_id: int, data):
    step = session.get(SequenceStep, step_id)
    if not step:
        return None
    for k, v in data.dict(exclude_unset=True).items():
        setattr(step, k, v)
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def delete_sequence_step(session: Session, step_id: int):
    step = session.get(SequenceStep, step_id)
    if not step:
        return False
    session.delete(step)
    session.commit()
    return True


# --------------------------------------------------------------------------- #
# Scheduling helpers
# --------------------------------------------------------------------------- #


def _already_scheduled_on(session: Session, date_: datetime.date) -> int:
    """Return how many emails are already scheduled for *date_* (00-24h)."""
    start = datetime.combine(date_, time(0, 0))
    end = start + timedelta(days=1)
    return (
        session.exec(
            select(func.count())
            .select_from(ScheduledEmail)
            .where(ScheduledEmail.send_at >= start, ScheduledEmail.send_at < end)
        )
        .one()
    )


# --------------------------------------------------------------------------- #
# Public scheduling API
# --------------------------------------------------------------------------- #


def bulk_assign_sequence_to_prospects(
    session: Session, prospect_ids: List[int], sequence_id: int
):
    # — ensure each prospect record carries the new sequence_id —
    for pid in prospect_ids:
        prospect = session.get(Prospect, pid)
        if prospect:
            prospect.sequence_id = sequence_id
            session.add(prospect)
    session.commit()

    steps = get_sequence_steps(session, sequence_id)
    if not steps:
        return

    today = datetime.utcnow().date()
    assignments_by_date: dict[datetime.date, list[tuple[int, SequenceStep]]] = {}

    for pid in prospect_ids:
        for step in steps:
            send_date = _get_next_working_day(today + timedelta(days=step.delay_days))
            assignments_by_date.setdefault(send_date, []).append((pid, step))

    for send_date, assignments in assignments_by_date.items():
        already = _already_scheduled_on(session, send_date)
        slots_left = settings.MAX_EMAILS_PER_DAY - already
        if slots_left <= 0:
            continue

        to_schedule = assignments[:slots_left]
        times = _random_times_for_window(send_date, len(to_schedule))

        for (pid, step), send_time in zip(to_schedule, times):
            scheduled = ScheduledEmail(
                prospect_id=pid,
                template_id=step.template_id,
                send_at=send_time,
                status="pending",
            )
            session.add(scheduled)

    session.commit()


def schedule_sequence_for_prospect(session: Session, prospect_id: int, sequence_id: int):
    steps = get_sequence_steps(session, sequence_id)
    if not steps:
        return
    today = datetime.utcnow().date()

    for step in steps:
        send_date = _get_next_working_day(today + timedelta(days=step.delay_days))
        already = _already_scheduled_on(session, send_date)
        if already >= settings.MAX_EMAILS_PER_DAY:
            continue
        send_time = _random_times_for_window(send_date, 1)[0]
        scheduled = ScheduledEmail(
            prospect_id=prospect_id,
            template_id=step.template_id,
            send_at=send_time,
            status="pending",
        )
        session.add(scheduled)
    session.commit()


def get_prospect_sequence_progress(session, prospect_id: int, sequence_id: int):
    if not sequence_id:
        return (0, 0)

    steps = list(
        session.exec(select(SequenceStep).where(SequenceStep.sequence_id == sequence_id))
    )
    total = len(steps)
    if total == 0:
        return (0, 0)

    template_ids = [s.template_id for s in steps]
    sent_count = (
        session.exec(
            select(func.count())
            .select_from(ScheduledEmail)
            .where(
                ScheduledEmail.prospect_id == prospect_id,
                ScheduledEmail.template_id.in_(template_ids),
                ScheduledEmail.status == "sent",
            )
        )
        .one()
    )

    return (sent_count, total)

