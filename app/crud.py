### app/crud.py
# This file implements database-level CRUD operations using SQLModel sessions.
# It handles operations for prospects, templates, sequences, steps, and scheduling logic.

from sqlmodel import Session, select
from app.models import Prospect, EmailTemplate, Sequence, SequenceStep, ScheduledEmail, EmailTemplateUpdate
from datetime import datetime, timedelta

# Prospects
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
    if prospect:
        session.delete(prospect)
        session.commit()

# Templates
def create_template(session: Session, template: EmailTemplate):
    session.add(template)
    session.commit()
    session.refresh(template)
    return template

def get_templates(session: Session):
    return session.exec(select(EmailTemplate)).all()

def delete_template(session: Session, template_id: int):
    template = session.get(EmailTemplate, template_id)
    if template:
        session.delete(template)
        session.commit()

def update_template(session: Session, template_id: int, data: EmailTemplateUpdate):
    db_template = session.get(EmailTemplate, template_id)
    if not db_template:
        return None
    data_dict = data.dict(exclude_unset=True)
    for key, value in data_dict.items():
        setattr(db_template, key, value)
    session.add(db_template)
    session.commit()
    session.refresh(db_template)
    return db_template

# Sequences
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

# Scheduling
def schedule_sequence_for_prospect(session: Session, prospect_id: int, sequence_id: int):
    steps = get_sequence_steps(session, sequence_id)
    now = datetime.utcnow()
    for index, step in enumerate(steps):
        send_time = now + timedelta(days=step.delay_days)
        scheduled = ScheduledEmail(
            prospect_id=prospect_id,
            template_id=step.template_id,
            send_at=send_time,
            status="pending"
        )
        session.add(scheduled)
    session.commit()

