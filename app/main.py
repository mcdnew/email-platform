# 📄 File: app/main.py

import os
import logging
from fastapi import FastAPI, HTTPException, Depends, status, Request
from sqlmodel import Session, select
from typing import Optional
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import get_session
from app.models import ScheduledEmail, Prospect, EmailTemplate, SentEmail, Sequence, SequenceStep
from app.schemas import TestEmailRequest, AssignSequenceRequest
from app.mailer import send_email
from app.config import settings
from app.routes import open_tracking
from app.dev import router as dev_router
from app import crud
import pytz
from datetime import datetime, time

app = FastAPI()
app.include_router(open_tracking.router)
app.include_router(dev_router)

# --- Constants ---
CET = pytz.timezone("Europe/Paris")

SEND_START = time(0, 0)
SEND_END = time(23, 59)

# --- Error Logging ---
ERROR_LOG_PATH = "error_log.txt"
error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
if not error_logger.handlers:
    file_handler = logging.FileHandler(ERROR_LOG_PATH)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    error_logger.addHandler(file_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_msg = f"URL: {request.url}\nMethod: {request.method}\nError: {repr(exc)}"
    error_logger.error(log_msg)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})

@app.get("/error-log")
def get_error_log():
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    if not os.path.exists(ERROR_LOG_PATH):
        return {"log": ""}
    with open(ERROR_LOG_PATH) as f:
        return {"log": f.read()}

@app.post("/clear-error-log")
def clear_error_log():
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    open(ERROR_LOG_PATH, "w").close()
    return {"message": "Error log cleared"}

def is_working_day(dt: datetime) -> bool:
    return dt.weekday() < 5

def is_within_window(dt: datetime) -> bool:
    return True  # For testing

def get_now_cet():
    return datetime.now(CET)

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
                break
            prospect = session.get(Prospect, email.prospect_id)
            template = session.get(EmailTemplate, email.template_id)
            if not prospect or not template:
                continue
            context = {
                "name": prospect.name,
                "email": prospect.email,
                "company": prospect.company or "",
                "title": prospect.title or ""
            }
            success = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=prospect.email if '@example.com' not in prospect.email else None,
                context=context
            )
            email.sent_at = datetime.utcnow()
            email.status = "sent" if success else "failed"
            sent_today += 1 if success else 0
            sent_record = SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=email.sent_at,
                status=email.status,
                prospect_id=prospect.id
            )
            session.add(email)
            session.add(sent_record)
            count += 1
        session.commit()
        print("Done.")
        return f"Scheduler processed {count} emails."

@app.post("/run-scheduler")
def run_scheduler_api():
    result = run_scheduler()
    return JSONResponse(content={"message": result})

@app.post("/force-scheduler")
def force_run_scheduler():
    print("Running scheduler in FORCE mode (ignoring limits)")
    with next(get_session()) as session:
        pending_emails = session.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending"
            )
        ).all()
        count = 0
        for email in pending_emails:
            prospect = session.get(Prospect, email.prospect_id)
            template = session.get(EmailTemplate, email.template_id)
            if not prospect or not template:
                continue
            context = {
                "name": prospect.name,
                "email": prospect.email,
                "company": prospect.company or "",
                "title": prospect.title or ""
            }
            success = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=prospect.email if '@example.com' not in prospect.email else None,
                context=context
            )
            email.sent_at = datetime.utcnow()
            email.status = "sent" if success else "failed"
            sent_record = SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=email.sent_at,
                status=email.status,
                prospect_id=prospect.id
            )
            session.add(email)
            session.add(sent_record)
            count += 1
        session.commit()
        print("Done.")
        return {"message": f"FORCE scheduler processed {count} emails."}

# --- Prospects API (with support for assigned param) ---
@app.get("/prospects")
def get_prospects(assigned: Optional[bool] = None, session: Session = Depends(get_session)):
    if assigned is None:
        prospects = crud.get_prospects(session)
    elif assigned:
        prospects = session.exec(select(Prospect).where(Prospect.sequence_id.is_not(None))).all()
    else:
        prospects = session.exec(select(Prospect).where(Prospect.sequence_id.is_(None))).all()
    # [rest of mapping/progress logic as in your working code...]
    sequences = {s.id: s.name for s in session.exec(select(Sequence)).all()}
    scheds = session.exec(select(ScheduledEmail)).all()
    steps_by_sequence = {}
    for s in session.exec(select(Sequence)).all():
        steps = session.exec(select(SequenceStep).where(SequenceStep.sequence_id == s.id)).all()
        steps_by_sequence[s.id] = len(steps)
    scheduled_by_prospect = {}
    for se in scheds:
        scheduled_by_prospect.setdefault(se.prospect_id, []).append(se)
    for v in scheduled_by_prospect.values():
        v.sort(key=lambda e: e.send_at or datetime.min)
    results = []
    for p in prospects:
        d = p.dict() if hasattr(p, "dict") else dict(p)
        seq_id = getattr(p, "sequence_id", None)
        d["sequence_name"] = sequences.get(seq_id) if seq_id else None
        total_steps = steps_by_sequence.get(seq_id, 0) if seq_id else 0
        scheduled = scheduled_by_prospect.get(p.id, [])
        cur_step = sum(1 for e in scheduled if e.status in ("sent", "failed"))
        d["sequence_steps_total"] = total_steps
        d["sequence_step_current"] = cur_step
        d["sequence_progress_pct"] = int((cur_step / total_steps) * 100) if total_steps else 0
        results.append(d)
    return results

@app.post("/prospects")
def add_prospect(p: Prospect, session: Session = Depends(get_session)):
    return crud.create_prospect(session, p)

@app.put("/prospects/{prospect_id}")
def update_prospect(prospect_id: int, updated: Prospect, session: Session = Depends(get_session)):
    db_p = session.get(Prospect, prospect_id)
    if not db_p:
        raise HTTPException(status_code=404, detail="Prospect not found")
    for key, value in updated.dict(exclude_unset=True).items():
        setattr(db_p, key, value)
    return crud.update_prospect(session, db_p)

@app.delete("/prospects/{prospect_id}")
def delete_prospect(prospect_id: int, session: Session = Depends(get_session)):
    ok = crud.delete_prospect(session, prospect_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return {"message": "Deleted"}


@app.post("/assign-sequence")
def assign_sequence(data: AssignSequenceRequest, session: Session = Depends(get_session)):
    ventilate_days = data.ventilate_days or 1
    # Parse start_date from string or fallback to today
    try:
        start_date = datetime.datetime.strptime(data.start_date, "%Y-%m-%d").date() if data.start_date else datetime.date.today()
    except Exception:
        start_date = datetime.date.today()
    # Validate prospect existence as before...
    for pid in data.prospect_ids:
        if not session.get(Prospect, pid):
            raise HTTPException(status_code=404, detail=f"Prospect {pid} not found")
    # Pass start_date to the bulk assign function!
    crud.bulk_assign_sequence_to_prospects(session, data.prospect_ids, data.sequence_id, ventilate_days, start_date)
    return {"message": f"Assigned sequence {data.sequence_id} to {len(data.prospect_ids)} prospects over {ventilate_days} days starting {start_date}"}

# --- Template API ---
@app.get("/templates")
def get_templates_route(session: Session = Depends(get_session)):
    return crud.get_templates(session)

@app.post("/templates")
def create_template(t: EmailTemplate, session: Session = Depends(get_session)):
    return crud.create_template(session, t)

@app.patch("/templates/{template_id}")
def update_template(template_id: int, update: EmailTemplate, session: Session = Depends(get_session)):
    db_template = session.get(EmailTemplate, template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(db_template, key, value)
    return crud.update_template(session, template_id, update)

@app.delete("/templates/{template_id}")
def delete_template(template_id: int, session: Session = Depends(get_session)):
    res = crud.delete_template(session, template_id)
    if res is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete template: it is still used in a sequence step. Remove those steps first."
        )
    elif res is False:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Deleted"}

# --- Sequence API ---
@app.get("/sequences")
def get_sequences(session: Session = Depends(get_session)):
    return crud.get_sequences(session)

@app.post("/sequences")
def create_sequence(s: Sequence, session: Session = Depends(get_session)):
    return crud.create_sequence(session, s)

@app.patch("/sequences/{sequence_id}")
def update_sequence(sequence_id: int, s: Sequence, session: Session = Depends(get_session)):
    db_sequence = session.get(Sequence, sequence_id)
    if not db_sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    for key, value in s.dict(exclude_unset=True).items():
        setattr(db_sequence, key, value)
    session.add(db_sequence)
    session.commit()
    session.refresh(db_sequence)
    return db_sequence

@app.delete("/sequences/{sequence_id}")
def delete_sequence(sequence_id: int, session: Session = Depends(get_session)):
    sequence = session.get(Sequence, sequence_id)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    session.delete(sequence)
    session.commit()
    return {"message": "Deleted"}

# --- Sequence Steps API ---
@app.get("/sequences/{sequence_id}/steps")
def get_steps_for_sequence(sequence_id: int, session: Session = Depends(get_session)):
    return crud.get_sequence_steps(session, sequence_id)

@app.post("/sequences/{sequence_id}/steps")
def add_step_to_sequence(sequence_id: int, step: SequenceStep, session: Session = Depends(get_session)):
    template = session.get(EmailTemplate, step.template_id)
    if not template:
        raise HTTPException(status_code=400, detail=f"Template id {step.template_id} does not exist")
    sequence = session.get(Sequence, sequence_id)
    if not sequence:
        raise HTTPException(status_code=400, detail=f"Sequence id {sequence_id} does not exist")
    step.sequence_id = sequence_id
    return crud.create_sequence_step(session, step)

@app.patch("/sequences/steps/{step_id}")
def update_sequence_step(step_id: int, updated: SequenceStep, session: Session = Depends(get_session)):
    res = crud.update_sequence_step(session, step_id, updated)
    if res is None:
        raise HTTPException(status_code=404, detail="Step not found")
    return res

@app.delete("/sequences/steps/{step_id}")
def delete_sequence_step(step_id: int, session: Session = Depends(get_session)):
    ok = crud.delete_sequence_step(session, step_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Deleted"}

# --- Sent Email, Analytics, Unsubscribe, Scheduler ---
@app.get("/sent-emails")
def get_sent_emails(session: Session = Depends(get_session)):
    sent = session.exec(select(SentEmail).order_by(SentEmail.sent_at.desc())).all()
    templates = {t.id: t.name for t in session.exec(select(EmailTemplate)).all()}
    sequences = {s.id: s.name for s in session.exec(select(Sequence)).all()}
    scheduled_lookup = {e.id: e.sequence_id for e in session.exec(select(ScheduledEmail)).all() if hasattr(e, 'sequence_id')}
    enriched = []
    for e in sent:
        d = e.dict() if hasattr(e, 'dict') else dict(e)
        d['template_name'] = templates.get(getattr(e, 'template_id', None))
        d['sequence_id'] = scheduled_lookup.get(getattr(e, 'scheduled_email_id', None)) or getattr(e, 'sequence_id', None)
        d['sequence_name'] = sequences.get(d['sequence_id']) if d['sequence_id'] else None
        enriched.append(d)
    return enriched

@app.get("/analytics/summary")
def get_analytics_summary(session: Session = Depends(get_session)):
    total_sent = session.exec(select(SentEmail)).all()
    total_failed = [e for e in total_sent if e.status == "failed"]
    total_opened = [e for e in total_sent if e.status == "opened"]
    sent_today = count_sent_today(session)
    return {
        "total_sent": len(total_sent),
        "total_failed": len(total_failed),
        "open_rate": round((len(total_opened) / len(total_sent)) * 100, 2) if total_sent else 0,
        "sent_today": sent_today,
        "recent": [
            {
                "to": e.to,
                "subject": e.subject,
                "status": e.status,
                "sent_at": e.sent_at,
                "template_name": getattr(e, 'template_name', None),
                "sequence_name": getattr(e, 'sequence_name', None)
            } for e in total_sent[:10]
        ]
    }

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

@app.get("/prospects/{prospect_id}/timeline")
def get_prospect_timeline(prospect_id: int, session: Session = Depends(get_session)):
    prospect = session.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found.")

    sequence_id = prospect.sequence_id
    scheduled = session.exec(
        select(ScheduledEmail)
        .where(ScheduledEmail.prospect_id == prospect_id)
    ).all()

    sched_by_tmpl = {}
    for s in scheduled:
        sched_by_tmpl.setdefault(s.template_id, []).append(s)

    template_map = {
        t.id: t for t in session.exec(select(EmailTemplate)).all()
    }

    timeline = []

    if sequence_id:
        steps = session.exec(
            select(SequenceStep)
            .where(SequenceStep.sequence_id == sequence_id)
            .order_by(SequenceStep.delay_days)
        ).all()

        for idx, step in enumerate(steps, start=1):
            tmpl = template_map.get(step.template_id)
            candidates = sched_by_tmpl.get(step.template_id, [])
            sched = min(candidates, key=lambda x: x.send_at, default=None)

            timeline.append({
                "step_number": idx,
                "template_name": tmpl.name if tmpl else "N/A",
                "subject": tmpl.subject if tmpl else "",
                "scheduled_at": sched.send_at if sched else None,
                "sent_at": sched.sent_at if sched else None,
                "status": sched.status if sched else "-",
                "opened_at": getattr(sched, "opened_at", None) if sched else None,
            })
    else:
        for sched in sorted(scheduled, key=lambda x: x.send_at or datetime.min):
            tmpl = template_map.get(sched.template_id)
            timeline.append({
                "step_number": None,
                "template_name": tmpl.name if tmpl else "N/A",
                "subject": tmpl.subject if tmpl else "",
                "scheduled_at": sched.send_at,
                "sent_at": sched.sent_at,
                "status": sched.status,
                "opened_at": getattr(sched, "opened_at", None),
            })

    return timeline

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

@app.post("/reset-all", status_code=status.HTTP_200_OK)
def reset_all(session: Session = Depends(get_session)):
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    for model in [SentEmail, ScheduledEmail, SequenceStep, Sequence, Prospect, EmailTemplate]:
        session.query(model).delete()
        session.commit()
    print("RESET ALL ENDPOINT HIT")
    return {"message": "All data deleted!"}

