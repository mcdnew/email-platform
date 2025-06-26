### app/main.py
# This file registers all FastAPI routes for the backend API.
# It includes endpoints for handling templates, prospects, sequences, test-sending emails, and more.

# 📄 File: app/main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlmodel import Session, select
from typing import Optional
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import get_session
from app.models import ScheduledEmail, Prospect, EmailTemplate, SentEmail, Sequence, SequenceStep
from app.schemas import TestEmailRequest, AssignSequenceRequest
from app.mailer import send_email
from app.config import settings
from app.routes import open_tracking

import pytz
import random
import time as time_module
from datetime import datetime, time

app = FastAPI()
app.include_router(open_tracking.router)

# --- Constants ---
CET = pytz.timezone("Europe/Paris")
SEND_START = time(9, 0)
SEND_END = time(21, 0)

# --- Helpers ---
def is_working_day(dt: datetime) -> bool:
    return dt.weekday() < 5

def is_within_window(dt: datetime) -> bool:
    return SEND_START <= dt.time() <= SEND_END

def get_now_cet():
    return datetime.now(CET)

def get_random_delay(min_sec=10, max_sec=90):
    return random.randint(min_sec, max_sec)

def count_sent_today(session) -> int:
    today = get_now_cet().date()
    results = session.exec(
        select(SentEmail).where(
            SentEmail.sent_at >= datetime.combine(today, time.min, tzinfo=CET),
            SentEmail.status == "sent"
        )
    )
    return len(list(results))

# --- Scheduler ---
def run_scheduler():
    print("Running email scheduler...")
    with next(get_session()) as session:
        now = get_now_cet()

        if not is_working_day(now) or not is_within_window(now):
            print("Outside allowed CET window.")
            return "Outside allowed CET window."

        sent_today = count_sent_today(session)
        if sent_today >= settings.MAX_EMAILS_PER_DAY:
            print("Daily email limit reached.")
            return "Daily limit reached."

        pending_emails = session.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.send_at <= now,
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending"
            )
        ).all()

        count = 0
        for email in pending_emails:
            if sent_today >= settings.MAX_EMAILS_PER_DAY:
                print("Reached limit mid-batch.")
                break

            prospect = session.get(Prospect, email.prospect_id)
            template = session.get(EmailTemplate, email.template_id)
            if not prospect or not template:
                continue

            time_module.sleep(get_random_delay())

            success = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=prospect.email if '@example.com' not in prospect.email else None
            )

            email.sent_at = get_now_cet()

            if success:
                email.status = "sent"
                sent_today += 1
                status = "sent"
            else:
                email.status = "failed"
                status = "failed"

            sent_record = SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=email.sent_at,
                status=status,
                prospect_id=prospect.id
            )

            session.add(email)
            session.add(sent_record)
            count += 1

        session.commit()
        print("Done.")
        return f"Scheduler processed {count} emails."

# --- API Routes ---
@app.get("/prospects")
def get_prospects(session: Session = Depends(get_session)):
    return session.exec(select(Prospect)).all()

@app.get("/templates")
def get_templates_route(session: Session = Depends(get_session)):
    return session.exec(select(EmailTemplate)).all()

@app.get("/sequences")
def get_sequences(session: Session = Depends(get_session)):
    return session.exec(select(Sequence)).all()

@app.post("/send-test")
def send_test_email(payload: TestEmailRequest):
    try:
        send_email(
            to_email=payload.email,
            subject=payload.subject,
            body=payload.body
        )
        return {"message": "Test email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-scheduler")
def run_scheduler_api():
    result = run_scheduler()
    return JSONResponse(content={"message": result})

@app.get("/sent-emails")
def get_sent_emails(session: Session = Depends(get_session)):
    return session.exec(select(SentEmail).order_by(SentEmail.sent_at.desc())).all()

@app.get("/analytics/summary")
def analytics_summary(session: Session = Depends(get_session)):
    try:
        now = get_now_cet()
        today_start = datetime.combine(now.date(), time.min, tzinfo=CET)

        all = session.exec(select(SentEmail)).all()
        total_sent = len([e for e in all if e.status == "sent"])
        total_opened = len([e for e in all if e.status == "opened"])
        total_failed = len([e for e in all if e.status == "failed"])

        # Handle both naive and aware datetime comparisons
        def is_today(e):
            if not e.sent_at:
                return False
            if e.sent_at.tzinfo is None:
                aware_time = e.sent_at.replace(tzinfo=CET)
            else:
                aware_time = e.sent_at
            return aware_time >= today_start

        sent_today = len([e for e in all if is_today(e)])
        open_rate = round((total_opened / total_sent) * 100, 1) if total_sent else 0

        recent = sorted(all, key=lambda x: x.sent_at or datetime.min, reverse=True)[:5]

        return {
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_failed": total_failed,
            "sent_today": sent_today,
            "open_rate": open_rate,
            "recent": [e.dict() for e in recent]
        }
    except Exception as e:
        print("❌ Error in /analytics/summary:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/unsubscribe")
def unsubscribe(token: str, session: Session = Depends(get_session)):
    from app.tracking import serializer
    try:
        email = serializer.loads(token)
        prospect = session.exec(select(Prospect).where(Prospect.email == email)).first()
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")
        prospect.unsubscribed = True
        session.add(prospect)
        session.commit()
        return HTMLResponse("""
            <html><body>
            <h3>You’ve been unsubscribed successfully.</h3>
            </body></html>
        """)
    except Exception:
        return HTMLResponse("<h3>Invalid or expired unsubscribe link.</h3>", status_code=400)

