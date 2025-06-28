# app/dev.py

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
import logging
from faker import Faker
from sqlalchemy import text

from app.database import get_session
from app.models import (
    Prospect,
    EmailTemplate,
    SentEmail,
    ScheduledEmail,
    Sequence,
    SequenceStep,
)

router = APIRouter(prefix="/dev", tags=["dev"])

def dev_only():
    """Raise error if not in DEV_MODE (for development safety)."""
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed outside DEV_MODE")

# --- Purge/reset by table ---
@router.post("/reset-table/{table}", status_code=status.HTTP_200_OK)
def reset_table(table: str, session: Session = Depends(get_session)):
    """
    Danger: Deletes all data from a single table.
    Only allowed in DEV_MODE.
    """
    dev_only()
    MODEL_MAP = {
        "prospects": Prospect,
        "templates": EmailTemplate,
        "sent_emails": SentEmail,
        "scheduled_emails": ScheduledEmail,
        "sequences": Sequence,
        "sequence_steps": SequenceStep,
    }
    model = MODEL_MAP.get(table)
    if not model:
        raise HTTPException(status_code=400, detail="Unknown table")
    deleted = session.query(model).delete(synchronize_session=False)
    session.commit()
    return {"message": f"All data from '{table}' deleted.", "deleted": deleted}

# --- Bulk insert dummy/test data ---
@router.post("/generate-prospects")
def generate_prospects(n: int = 10, session: Session = Depends(get_session)):
    """
    Add N fake prospects for demo/load testing.
    Only allowed in DEV_MODE.
    """
    dev_only()
    fake = Faker()
    prospects = []
    for _ in range(n):
        p = Prospect(
            name=fake.name(),
            email=fake.unique.email(),
            company=fake.company(),
            title=fake.job(),
        )
        session.add(p)
        prospects.append(p)
    session.commit()
    return {"added": len(prospects)}

@router.post("/generate-templates")
def generate_templates(n: int = 5, session: Session = Depends(get_session)):
    """
    Add N fake email templates for demo/load testing.
    Only allowed in DEV_MODE.
    """
    dev_only()
    fake = Faker()
    templates = []
    for _ in range(n):
        t = EmailTemplate(
            name=fake.catch_phrase(),
            subject=fake.sentence(nb_words=6),
            body=f"<p>Hello {{name}}, {fake.text(max_nb_chars=80)}</p>",
        )
        session.add(t)
        templates.append(t)
    session.commit()
    return {"added": len(templates)}

# --- Toggle logging level ---
@router.post("/log-level")
def set_log_level(level: str):
    """
    Set Python logger level for backend (DEBUG, ERROR, etc).
    Only allowed in DEV_MODE.
    """
    dev_only()
    logger = logging.getLogger()
    allowed = ["DEBUG", "ERROR", "INFO", "WARNING", "CRITICAL"]
    if level.upper() not in allowed:
        raise HTTPException(status_code=400, detail="Invalid log level.")
    logger.setLevel(level.upper())
    return {"message": f"Log level set to {level.upper()}"}

# --- Hard reset: delete all and reset IDs ---
@router.post("/reset-all-hard", status_code=status.HTTP_200_OK)
def reset_all_hard(session: Session = Depends(get_session)):
    """
    DANGER: Hard reset of all tables, including resetting auto-increment IDs.
    Only for testing/dev, requires DEV_MODE.
    """
    dev_only()
    try:
        session.execute(text("""
            TRUNCATE TABLE
                sentemail,
                scheduledemail,
                sequencestep,
                sequence,
                prospect,
                emailtemplate
            RESTART IDENTITY CASCADE;
        """))
        session.commit()
        return {"message": "All data deleted, IDs reset!"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"TRUNCATE failed: {e}")

# --- (Extend with error log or more dev endpoints as needed) ---

