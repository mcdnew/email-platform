# app/main.py

import json
import os
import logging
from datetime import datetime, date, time
from typing import List, Optional

import pytz
from fastapi import FastAPI, HTTPException, Depends, Request, Security, status
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Session, select, update
from sqlalchemy import func, delete
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.models import (
    Prospect, EmailTemplate, Sequence, SequenceStep,
    ScheduledEmail, SentEmail, SmtpSettings,
)
from app.schemas import (
    AssignSequenceRequest, SequenceCreate, SequenceRead, TestEmailRequest,
    ProspectImport, StepReorderRequest,
)
from app.mailer import send_email
from app.config import settings
from app.tracking import load_unsubscribe_token
from app.logging_config import configure_logging
from app import crud
from app.routes import open_tracking
from app.dev import router as dev_router

# ────────────── Structured JSON Logging ──────────────
configure_logging(log_path=settings.LOG_PATH, level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ────────────── App & Routers ──────────────
app = FastAPI()
app.include_router(open_tracking.router)
app.include_router(dev_router)

# ────────────── API Key Auth ──────────────
#
# All endpoints require X-API-Key: <settings.API_KEY>.
# Set API_KEY in .env. If API_KEY is empty (dev/test), auth is disabled.
#
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(api_key: str = Security(_api_key_header)):
    if not settings.API_KEY:
        return  # auth disabled when API_KEY is unset (dev/test only)
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# ────────────── Constants ──────────────
CET        = pytz.timezone(settings.TIMEZONE)
SEND_START = time(0, 0)
SEND_END   = time(23, 59)

@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        extra={"url": str(request.url), "method": request.method, "error": repr(exc)},
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal error"})

@app.get("/error-log", dependencies=[Depends(require_api_key)])
def get_error_log():
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    if not os.path.exists(settings.LOG_PATH):
        return {"entries": []}
    entries = []
    with open(settings.LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"event": line})  # fallback for legacy plain-text lines
    return {"entries": entries}

@app.post("/clear-error-log", dependencies=[Depends(require_api_key)])
def clear_error_log():
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    with open(settings.LOG_PATH, "w"):
        pass
    return {"message": "Error log cleared"}

@app.get("/cron-log", dependencies=[Depends(require_api_key)])
def cron_log():
    path = "logs/cron_invocations.log"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Cron log file not found")
    with open(path) as f:
        lines = [line.strip() for line in f if "Cron job fired" in line]
    return {"lines": lines[-10:]}

# ────────────── Helpers ──────────────
def _now() -> datetime:
    return datetime.now(CET)

def _is_working(d: datetime) -> bool:
    return d.weekday() < 5

def _name_lookup(db: Session, model) -> dict:
    """Return {id: name} dict for any model with .id and .name fields."""
    return {row.id: row.name for row in db.exec(select(model)).all()}

def _scalar(db: Session, stmt) -> int:
    res = db.exec(stmt).one_or_none()
    if res is None:
        return 0
    if isinstance(res, (list, tuple)):
        return res[0]
    return int(res)

def _sent_today(db: Session) -> int:
    today = _now().date()
    stmt = (
        select(func.count()).select_from(SentEmail)
        .where(
            SentEmail.sent_at >= datetime.combine(today, time.min, tzinfo=CET),
            SentEmail.status == "sent",
        )
    )
    return _scalar(db, stmt)

# ────────────── Scheduler ──────────────
#
# Status flow for ScheduledEmail:
#   pending → sending (DB lock claimed)
#             → sent   (SMTP success)
#             → failed (SMTP failure)
#
# The "sending" lock prevents concurrent scheduler runs from
# processing the same row (double-send protection).

def _process_emails(db: Session, enforce_limits: bool = True) -> str:
    """
    Core send loop. Called by both /run-scheduler and /force-scheduler.

    enforce_limits=True  → respect send window and daily cap (normal cron)
    enforce_limits=False → ignore window and cap (force/manual send)

    db is injected by FastAPI via Depends(get_session) so the test DB
    override in conftest.py applies automatically.
    """
    now = _now()

    if enforce_limits:
        if not (_is_working(now) and SEND_START <= now.time() <= SEND_END):
            logger.debug("scheduler_skipped", extra={"reason": "outside_window"})
            return "outside window"
        sent_today = _sent_today(db)
        if sent_today >= settings.MAX_EMAILS_PER_DAY:
            logger.warning("daily_limit_reached", extra={"sent_today": sent_today, "limit": settings.MAX_EMAILS_PER_DAY})
            return "daily limit reached"
    else:
        sent_today = 0

    # Load DB-overridden SMTP settings (if configured via /settings/smtp)
    smtp_row = db.get(SmtpSettings, 1)
    smtp_override = None
    if smtp_row:
        smtp_override = {
            "smtp_server":   smtp_row.smtp_server,
            "smtp_port":     smtp_row.smtp_port,
            "smtp_user":     smtp_row.smtp_user,
            "smtp_password": smtp_row.smtp_password,
        }

    # Claim pending rows atomically: pending → sending
    # Any concurrent call will find 0 rows in this batch.
    rows_to_claim = db.exec(
        select(ScheduledEmail).where(
            ScheduledEmail.send_at <= now,
            ScheduledEmail.status == "pending",
            ScheduledEmail.sent_at.is_(None),
        )
    ).all()

    if not rows_to_claim:
        return "processed 0"

    claimed_ids = [r.id for r in rows_to_claim]
    db.exec(
        update(ScheduledEmail)
        .where(ScheduledEmail.id.in_(claimed_ids))
        .values(status="sending")
    )
    db.commit()

    # Re-fetch the claimed rows (status is now "sending")
    pending = db.exec(
        select(ScheduledEmail).where(ScheduledEmail.id.in_(claimed_ids))
    ).all()

    processed = 0
    for sched in pending:
        if enforce_limits and sent_today >= settings.MAX_EMAILS_PER_DAY:
            sched.status = "pending"
            db.add(sched)
            continue

        prospect = db.get(Prospect, sched.prospect_id)
        template = db.get(EmailTemplate, sched.template_id)

        if not (prospect and template):
            logger.warning("email_skipped_missing", extra={"scheduled_email_id": sched.id, "prospect_id": sched.prospect_id})
            sched.status = "failed"
            db.add(sched)
            continue

        if prospect.unsubscribed:
            logger.info("email_skipped_unsubscribed", extra={"prospect_id": prospect.id, "to": prospect.email})
            sched.status = "failed"
            db.add(sched)
            continue

        seq = db.get(Sequence, sched.sequence_id) if sched.sequence_id else None
        bcc = getattr(seq, "bcc_email", None)
        ctx = {
            "name":    prospect.name,
            "email":   prospect.email,
            "company": prospect.company or "",
            "title":   prospect.title or "",
        }

        # Pre-insert SentEmail to get an ID for the tracking pixel.
        sent_ts = datetime.utcnow()
        sent_record = SentEmail(
            to=prospect.email,
            subject=template.subject,
            body=template.body,
            sent_at=sent_ts,
            status="sending",
            prospect_id=prospect.id,
            template_id=template.id,
            sequence_id=sched.sequence_id,
        )
        db.add(sent_record)
        db.flush()  # assigns sent_record.id without committing

        send_result = send_email(
            to_email=prospect.email,
            subject=template.subject,
            body=template.body,
            bcc_email=bcc,
            context=ctx,
            email_id=sent_record.id,
            smtp_override=smtp_override,
        )

        sent_record.status = send_result
        sched.sent_at = sent_ts
        sched.status  = send_result

        db.add(sched)
        db.add(sent_record)

        if send_result == "sent":
            logger.info("email_sent", extra={
                "email_id": sent_record.id, "prospect_id": prospect.id,
                "to": prospect.email, "template_id": template.id,
            })
            processed += 1
            sent_today += 1
        elif send_result == "bounced":
            logger.warning("email_bounced", extra={
                "email_id": sent_record.id, "prospect_id": prospect.id, "to": prospect.email,
            })
            # Auto-suppress bounced prospects so they never receive email again
            prospect.unsubscribed = True
            db.add(prospect)
        else:
            logger.warning("email_failed", extra={
                "email_id": sent_record.id, "prospect_id": prospect.id, "to": prospect.email,
            })

    db.commit()
    return f"processed {processed}"


@app.post("/run-scheduler", dependencies=[Depends(require_api_key)])
def run_scheduler_api(db: Session = Depends(get_session)):
    return {"message": _process_emails(db, enforce_limits=True)}


@app.post("/force-scheduler", dependencies=[Depends(require_api_key)])
def force_scheduler(db: Session = Depends(get_session)):
    result = _process_emails(db, enforce_limits=False)
    return {"message": f"FORCE scheduler: {result}"}


@app.post("/retry-failed", dependencies=[Depends(require_api_key)])
def retry_failed(db: Session = Depends(get_session)):
    """
    Reset transient failed emails to pending and immediately run the scheduler.

    Skips permanently failed emails:
      - prospect deleted or template deleted
      - prospect is unsubscribed

    Each call increments retry_count. Emails that have reached MAX_RETRIES
    are not retried again.
    """
    candidates = db.exec(
        select(ScheduledEmail).where(
            ScheduledEmail.status == "failed",
            ScheduledEmail.retry_count < settings.MAX_RETRIES,
        )
    ).all()

    retried = 0
    for sched in candidates:
        prospect = db.get(Prospect, sched.prospect_id)
        template = db.get(EmailTemplate, sched.template_id)
        # Skip permanently failed cases — no point retrying
        if not (prospect and template) or prospect.unsubscribed:
            continue
        sched.status = "pending"
        sched.retry_count += 1
        sched.send_at = _now()
        sched.sent_at = None  # allow _process_emails to re-claim this row
        db.add(sched)
        retried += 1

    db.commit()

    if retried == 0:
        return {"message": "no retryable emails found", "retried": 0}

    result = _process_emails(db, enforce_limits=False)
    return {"message": f"retried {retried}: {result}", "retried": retried}


# ────────────── Scheduled-Email API for the UI ──────────────
@app.get("/scheduled-emails", dependencies=[Depends(require_api_key)])
def list_scheduled(db: Session = Depends(get_session)):
    sched = db.exec(select(ScheduledEmail)).all()
    tmpl  = {t.id: t for t in db.exec(select(EmailTemplate)).all()}
    pros  = {p.id: p for p in db.exec(select(Prospect)).all()}
    return [
        {
            "id":             s.id,
            "prospect_id":    s.prospect_id,
            "prospect_name":  pros[s.prospect_id].name if s.prospect_id in pros else None,
            "prospect_email": pros[s.prospect_id].email if s.prospect_id in pros else None,
            "template_id":    s.template_id,
            "template_name":  tmpl[s.template_id].name if s.template_id in tmpl else None,
            "send_at":        s.send_at,
            "sent_at":        s.sent_at,
            "status":         s.status,
        }
        for s in sched
    ]

class ScheduledEmailPatch(BaseModel):
    send_at: Optional[datetime] = None
    template_id: Optional[int] = None

@app.patch("/scheduled-emails/{sid}", dependencies=[Depends(require_api_key)])
def patch_schedule(sid: int, data: ScheduledEmailPatch, db: Session = Depends(get_session)):
    obj = db.get(ScheduledEmail, sid)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    if obj.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending emails can be edited")
    if data.send_at is not None:
        obj.send_at = data.send_at
    if data.template_id is not None:
        if not db.get(EmailTemplate, data.template_id):
            raise HTTPException(status_code=404, detail="Template not found")
        obj.template_id = data.template_id
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"message": "updated"}

@app.delete("/scheduled-emails/{sid}", dependencies=[Depends(require_api_key)])
def delete_schedule(sid: int, db: Session = Depends(get_session)):
    obj = db.get(ScheduledEmail, sid)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "deleted"}

@app.post("/scheduled-emails/{sid}/mark-sent", dependencies=[Depends(require_api_key)])
def mark_sent(sid: int, db: Session = Depends(get_session)):
    obj = db.get(ScheduledEmail, sid)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    obj.status  = "sent"
    obj.sent_at = _now()
    db.add(obj)
    db.commit()
    return {"message": "marked sent"}

# ────────────── Prospects CRUD/List ──────────────
#
# Paginated, sorted, and searchable. Response shape:
#   { items: [...], total: N, page: P, per_page: PP, pages: PG }
#
_PROSPECT_SORT = {
    "name":       Prospect.name,
    "email":      Prospect.email,
    "company":    Prospect.company,
    "created_at": Prospect.created_at,
}

@app.get("/prospects", dependencies=[Depends(require_api_key)])
def list_prospects(
    assigned:     Optional[str] = None,
    unsubscribed: Optional[str] = None,
    page:         int = 1,
    per_page:     int = 50,
    sort_by:      str = "name",
    order:        str = "asc",
    search:       Optional[str] = None,
    db: Session = Depends(get_session),
):
    page     = max(1, page)
    per_page = min(200, max(1, per_page))

    # Build filter list
    filters = []
    if assigned is not None:
        flag = str(assigned).lower() in {"1", "true", "yes", "on"}
        filters.append(Prospect.sequence_id.is_not(None) if flag else Prospect.sequence_id.is_(None))
    if unsubscribed is not None:
        flag = str(unsubscribed).lower() in {"1", "true", "yes", "on"}
        filters.append(Prospect.unsubscribed == flag)
    if search:
        term = f"%{search}%"
        filters.append(
            (Prospect.name.ilike(term)) |
            (Prospect.email.ilike(term)) |
            (Prospect.company.ilike(term))
        )

    # Count (no offset/limit)
    total = _scalar(db, select(func.count()).select_from(Prospect).where(*filters))

    # Sorted + paginated fetch
    col = _PROSPECT_SORT.get(sort_by, Prospect.name)
    prospects = db.exec(
        select(Prospect)
        .where(*filters)
        .order_by(col.desc() if order == "desc" else col.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    # Enrichment (same as before)
    step_counts = db.exec(
        select(SequenceStep.sequence_id, func.count(SequenceStep.id))
        .group_by(SequenceStep.sequence_id)
    ).all()
    steps_per_seq = {seq_id: cnt for seq_id, cnt in step_counts}

    prospect_ids = [p.id for p in prospects]
    sched_map: dict = {}
    if prospect_ids:
        for s in db.exec(
            select(ScheduledEmail).where(ScheduledEmail.prospect_id.in_(prospect_ids))
        ).all():
            sched_map.setdefault(s.prospect_id, []).append(s)

    seq_names = {s.id: s.name for s in db.exec(select(Sequence)).all()}

    items = []
    for p in prospects:
        total_steps = steps_per_seq.get(p.sequence_id, 0)
        done = sum(1 for s in sched_map.get(p.id, []) if s.status in {"sent", "failed"})
        items.append({
            **p.dict(),
            "sequence_name":         seq_names.get(p.sequence_id),
            "sequence_steps_total":  total_steps,
            "sequence_step_current": done,
            "sequence_progress_pct": int(100 * done / total_steps) if total_steps else 0,
        })

    return {
        "items":    items,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


@app.post("/prospects/bulk", dependencies=[Depends(require_api_key)])
def bulk_import_prospects(items: List[ProspectImport], db: Session = Depends(get_session)):
    """Accept a JSON array of prospects (parsed CSV from the frontend). Skip duplicates."""
    imported = skipped = 0
    errors = []
    for item in items:
        try:
            crud.create_prospect(db, Prospect(
                name=item.name, email=item.email,
                company=item.company, title=item.title,
            ))
            imported += 1
        except IntegrityError:
            db.rollback()
            skipped += 1
        except Exception as exc:
            db.rollback()
            errors.append({"email": item.email, "error": str(exc)})
    return {"imported": imported, "skipped": skipped, "errors": errors}

@app.post("/prospects", dependencies=[Depends(require_api_key)])
def add_prospect(p: Prospect, db: Session = Depends(get_session)):
    try:
        return crud.create_prospect(db, p)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A prospect with this email already exists")

@app.put("/prospects/{pid}", dependencies=[Depends(require_api_key)])
def edit_prospect(pid: int, data: Prospect, db: Session = Depends(get_session)):
    obj = db.get(Prospect, pid)
    if not obj:
        raise HTTPException(status_code=404, detail="Prospect not found")
    updates = data.dict(exclude_unset=True)
    if "sequence_id" in updates and updates["sequence_id"] is None:
        db.exec(delete(ScheduledEmail).where(ScheduledEmail.prospect_id == pid))
    for k, v in updates.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.delete("/prospects/{pid}", dependencies=[Depends(require_api_key)])
def delete_prospect(pid: int, db: Session = Depends(get_session)):
    if not crud.delete_prospect(db, pid):
        raise HTTPException(status_code=404, detail="Prospect not found")
    return {"message": "deleted"}

# ────────────── Assign Sequence / Bulk Scheduling ──────────────
@app.post("/assign-sequence", dependencies=[Depends(require_api_key)])
def assign_sequence(payload: AssignSequenceRequest, db: Session = Depends(get_session)):
    start = date.today()
    if payload.start_date:
        start = datetime.strptime(payload.start_date, "%Y-%m-%d").date()
    crud.bulk_assign_sequence_to_prospects(
        db, payload.prospect_ids, payload.sequence_id,
        ventilate_days=payload.ventilate_days or 0,
        start_date=start
    )
    return {"message": "sequence assigned"}

# ────────────── Sequence CRUD & Steps ──────────────
@app.get("/sequences", response_model=List[SequenceRead], dependencies=[Depends(require_api_key)])
def list_sequences(db: Session = Depends(get_session)):
    return db.exec(select(Sequence)).all()

@app.post("/sequences", response_model=SequenceRead, dependencies=[Depends(require_api_key)])
def create_sequence(data: SequenceCreate, db: Session = Depends(get_session)):
    obj = Sequence(**data.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.patch("/sequences/{sid}", response_model=SequenceRead, dependencies=[Depends(require_api_key)])
def update_sequence(sid: int, data: SequenceCreate, db: Session = Depends(get_session)):
    obj = db.get(Sequence, sid)
    if not obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.delete("/sequences/{sid}", dependencies=[Depends(require_api_key)])
def delete_sequence(sid: int, db: Session = Depends(get_session)):
    obj = db.get(Sequence, sid)
    if not obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    db.exec(delete(SequenceStep).where(SequenceStep.sequence_id == sid))
    db.exec(delete(ScheduledEmail).where(ScheduledEmail.sequence_id == sid))
    db.delete(obj); db.commit()
    return {"message": "deleted"}

@app.get("/sequences/{sid}/steps", dependencies=[Depends(require_api_key)])
def list_steps(sid: int, db: Session = Depends(get_session)):
    return crud.get_sequence_steps(db, sid)

@app.post("/sequences/{sid}/steps", dependencies=[Depends(require_api_key)])
def add_step(sid: int, step: SequenceStep, db: Session = Depends(get_session)):
    if not db.get(Sequence, sid):
        raise HTTPException(status_code=400, detail="Sequence not found")
    if not db.get(EmailTemplate, step.template_id):
        raise HTTPException(status_code=400, detail="Template not found")
    step.sequence_id = sid
    return crud.create_sequence_step(db, step)

@app.patch("/sequences/steps/{step_id}", dependencies=[Depends(require_api_key)])
def edit_step(step_id: int, data: SequenceStep, db: Session = Depends(get_session)):
    res = crud.update_sequence_step(db, step_id, data)
    if res is None:
        raise HTTPException(status_code=404, detail="Step not found")
    return res

@app.delete("/sequences/steps/{step_id}", dependencies=[Depends(require_api_key)])
def delete_step(step_id: int, db: Session = Depends(get_session)):
    if not crud.delete_sequence_step(db, step_id):
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "deleted"}

@app.post("/sequences/{sid}/reorder", dependencies=[Depends(require_api_key)])
def reorder_steps(sid: int, payload: StepReorderRequest, db: Session = Depends(get_session)):
    """Update delay_days for each step — persists drag-and-drop order from the frontend."""
    if not db.get(Sequence, sid):
        raise HTTPException(status_code=404, detail="Sequence not found")
    for item in payload.steps:
        step = db.get(SequenceStep, item.step_id)
        if step and step.sequence_id == sid:
            step.delay_days = item.delay_days
            db.add(step)
    db.commit()
    return {"message": "reordered"}

# ────────────── Templates CRUD ──────────────
@app.get("/templates", dependencies=[Depends(require_api_key)])
def list_templates(db: Session = Depends(get_session)):
    return crud.get_templates(db)

@app.post("/templates", dependencies=[Depends(require_api_key)])
def create_template(t: EmailTemplate, db: Session = Depends(get_session)):
    return crud.create_template(db, t)

@app.patch("/templates/{tid}", dependencies=[Depends(require_api_key)])
def update_template(tid: int, data: EmailTemplate, db: Session = Depends(get_session)):
    tpl = db.get(EmailTemplate, tid)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return crud.update_template(db, tid, data)

@app.delete("/templates/{tid}", dependencies=[Depends(require_api_key)])
def delete_template(tid: int, db: Session = Depends(get_session)):
    db.exec(delete(ScheduledEmail).where(
        ScheduledEmail.template_id == tid,
        ScheduledEmail.sent_at.is_(None)
    ))
    res = crud.delete_template(db, tid)
    if res is None:
        raise HTTPException(status_code=400, detail="Template used in a sequence step")
    if res is False:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "deleted"}

# ────────────── Sent Emails & Analytics ──────────────
_SENT_SORT = {
    "sent_at": SentEmail.sent_at,
    "status":  SentEmail.status,
    "to":      SentEmail.to,
}

@app.get("/sent-emails", dependencies=[Depends(require_api_key)])
def list_sent(
    page:          int = 1,
    per_page:      int = 50,
    sort_by:       str = "sent_at",
    order:         str = "desc",
    status_filter: Optional[str] = None,
    db: Session = Depends(get_session),
):
    page     = max(1, page)
    per_page = min(200, max(1, per_page))

    filters = []
    if status_filter:
        filters.append(SentEmail.status == status_filter)

    total = _scalar(db, select(func.count()).select_from(SentEmail).where(*filters))

    col = _SENT_SORT.get(sort_by, SentEmail.sent_at)
    sent = db.exec(
        select(SentEmail)
        .where(*filters)
        .order_by(col.desc() if order == "desc" else col.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    tnames = _name_lookup(db, EmailTemplate)
    snames = _name_lookup(db, Sequence)
    items = [
        {**e.dict(), "template_name": tnames.get(e.template_id), "sequence_name": snames.get(e.sequence_id)}
        for e in sent
    ]

    return {
        "items":    items,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }

@app.get("/analytics/summary", dependencies=[Depends(require_api_key)])
def analytics(db: Session = Depends(get_session)):
    # COUNT queries — no full table scan
    total  = _scalar(db, select(func.count()).select_from(SentEmail))
    failed = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.status == "failed"))
    opened = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.status == "opened"))
    recent = db.exec(select(SentEmail).order_by(SentEmail.sent_at.desc()).limit(10)).all()
    tnames = _name_lookup(db, EmailTemplate)
    snames = _name_lookup(db, Sequence)
    return {
        "total_sent":   total,
        "total_failed": failed,
        "open_rate":    round(opened / total * 100, 2) if total else 0,
        "sent_today":   _sent_today(db),
        "recent": [
            {
                "to":            e.to,
                "subject":       e.subject,
                "status":        e.status,
                "sent_at":       e.sent_at,
                "template_name": tnames.get(e.template_id),
                "sequence_name": snames.get(e.sequence_id),
            }
            for e in recent
        ],
    }

@app.get("/analytics/by-template", dependencies=[Depends(require_api_key)])
def analytics_by_template(db: Session = Depends(get_session)):
    templates = db.exec(select(EmailTemplate)).all()
    result = []
    for t in templates:
        sent   = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.template_id == t.id))
        opened = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.template_id == t.id, SentEmail.status == "opened"))
        failed = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.template_id == t.id, SentEmail.status.in_(["failed", "bounced"])))
        if sent == 0:
            continue
        result.append({
            "id": t.id,
            "name": t.name,
            "subject": t.subject,
            "sent": sent,
            "opened": opened,
            "failed": failed,
            "open_rate": round(opened / sent * 100, 1) if sent else 0,
        })
    return sorted(result, key=lambda x: x["sent"], reverse=True)


@app.get("/analytics/by-sequence", dependencies=[Depends(require_api_key)])
def analytics_by_sequence(db: Session = Depends(get_session)):
    sequences = db.exec(select(Sequence)).all()
    result = []
    for s in sequences:
        sent   = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.sequence_id == s.id))
        opened = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.sequence_id == s.id, SentEmail.status == "opened"))
        failed = _scalar(db, select(func.count()).select_from(SentEmail).where(SentEmail.sequence_id == s.id, SentEmail.status.in_(["failed", "bounced"])))
        if sent == 0:
            continue
        result.append({
            "id": s.id,
            "name": s.name,
            "sent": sent,
            "opened": opened,
            "failed": failed,
            "open_rate": round(opened / sent * 100, 1) if sent else 0,
        })
    return sorted(result, key=lambda x: x["sent"], reverse=True)


@app.post("/send-test", dependencies=[Depends(require_api_key)])
def send_test_email(data: TestEmailRequest, db: Session = Depends(get_session)):
    smtp_row = db.get(SmtpSettings, 1)
    smtp_override = None
    if smtp_row:
        smtp_override = {
            "smtp_server":   smtp_row.smtp_server,
            "smtp_port":     smtp_row.smtp_port,
            "smtp_user":     smtp_row.smtp_user,
            "smtp_password": smtp_row.smtp_password,
        }
    ok = send_email(
        to_email=data.email,
        subject=data.subject,
        body=data.body,
        context={"name": "Test Name", "title": "Test Title", "company": "Test Company", "email": data.email},
        smtp_override=smtp_override,
    )
    if ok != "sent":
        raise HTTPException(status_code=500, detail="SMTP failed")
    return {"message": "sent"}

@app.get("/prospects/{pid}/timeline", dependencies=[Depends(require_api_key)])
def timeline(pid: int, db: Session = Depends(get_session)):
    prospect = db.get(Prospect, pid)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    sched = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == pid)).all()

    if prospect.sequence_id:
        steps = db.exec(
            select(SequenceStep)
            .where(SequenceStep.sequence_id == prospect.sequence_id)
            .order_by(SequenceStep.delay_days)
        ).all()
        step_tids = {s.template_id for s in steps}
        tmpl = {t.id: t for t in db.exec(
            select(EmailTemplate).where(EmailTemplate.id.in_(step_tids))
        ).all()}
        tl = []
        for idx, step in enumerate(steps, 1):
            match = next((s for s in sched if s.template_id == step.template_id), None)
            et = tmpl.get(step.template_id)
            tl.append({
                "step_number":   idx,
                "template_name": et.name if et else "-",
                "subject":       et.subject if et else "",
                "scheduled_at":  getattr(match, "send_at", None),
                "sent_at":       getattr(match, "sent_at", None),
                "status":        getattr(match, "status", "-") if match else "-",
                "opened_at":     getattr(match, "opened_at", None) if match else None,
            })
        return tl

    sched_tids = {s.template_id for s in sched}
    tmpl = {t.id: t for t in db.exec(
        select(EmailTemplate).where(EmailTemplate.id.in_(sched_tids))
    ).all()}
    return sorted([
        {
            "step_number":   None,
            "template_name": tmpl[s.template_id].name if s.template_id in tmpl else "-",
            "subject":       tmpl[s.template_id].subject if s.template_id in tmpl else "",
            "scheduled_at":  s.send_at,
            "sent_at":       s.sent_at,
            "status":        s.status,
            "opened_at":     getattr(s, "opened_at", None),
        }
        for s in sched
    ], key=lambda x: x["scheduled_at"] or datetime.min)


@app.get("/unsubscribe")
def unsubscribe(token: str, db: Session = Depends(get_session)):
    """Unsubscribe endpoint — no API key required (linked from emails)."""
    from sqlalchemy import delete as sa_delete

    email = load_unsubscribe_token(token)
    if not email:
        err_html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Invalid Link</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#f9fafb;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:48px 40px;max-width:440px;width:100%;text-align:center}
.icon{font-size:48px;margin-bottom:16px}h1{font-size:22px;font-weight:600;color:#111827;margin-bottom:10px}
p{font-size:15px;color:#6b7280;line-height:1.6}</style></head>
<body><div class="card"><div class="icon">✕</div>
<h1>Invalid or expired link</h1>
<p>This unsubscribe link is no longer valid.<br>Please contact the sender directly if you wish to unsubscribe.</p>
</div></body></html>"""
        return HTMLResponse(err_html, status_code=400)

    prospect = db.exec(select(Prospect).where(Prospect.email == email)).first()
    if prospect:
        prospect.unsubscribed = True
        db.add(prospect)
        # Purge pending emails so the scheduler never sends them
        db.exec(
            sa_delete(ScheduledEmail).where(
                ScheduledEmail.prospect_id == prospect.id,
                ScheduledEmail.status == "pending",
            )
        )
        db.commit()

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribed</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#f9fafb;display:flex;align-items:center;
         justify-content:center;min-height:100vh;padding:24px}
    .card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;
          padding:48px 40px;max-width:440px;width:100%;text-align:center}
    .icon{font-size:48px;margin-bottom:16px}
    h1{font-size:22px;font-weight:600;color:#111827;margin-bottom:10px}
    p{font-size:15px;color:#6b7280;line-height:1.6}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✓</div>
    <h1>You've been unsubscribed</h1>
    <p>You won't receive any more emails from this sender.<br>
       If this was a mistake, please contact the sender directly.</p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.post("/reset-all", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_key)])
def reset_all(db: Session = Depends(get_session)):
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    for model in (SentEmail, ScheduledEmail, SequenceStep, Sequence, Prospect, EmailTemplate):
        db.query(model).delete()
        db.commit()
    return {"message": "all data deleted"}


# ────────────── SMTP Settings ──────────────

class SmtpSettingsPayload(BaseModel):
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_bcc: Optional[str] = None


@app.get("/settings/smtp", dependencies=[Depends(require_api_key)])
def get_smtp_settings(db: Session = Depends(get_session)):
    row = db.get(SmtpSettings, 1)
    if not row:
        # Return env-based defaults (mask password)
        return {
            "smtp_server": settings.SMTP_SERVER,
            "smtp_port": settings.SMTP_PORT,
            "smtp_user": settings.SMTP_USER,
            "smtp_password": "",
            "smtp_bcc": settings.SMTP_BCC,
            "source": "env",
        }
    return {
        "smtp_server": row.smtp_server or settings.SMTP_SERVER,
        "smtp_port": row.smtp_port or settings.SMTP_PORT,
        "smtp_user": row.smtp_user or settings.SMTP_USER,
        "smtp_password": "",  # never return password
        "smtp_bcc": row.smtp_bcc if row.smtp_bcc is not None else settings.SMTP_BCC,
        "source": "db",
    }


@app.put("/settings/smtp", dependencies=[Depends(require_api_key)])
def update_smtp_settings(payload: SmtpSettingsPayload, db: Session = Depends(get_session)):
    row = db.get(SmtpSettings, 1)
    if not row:
        row = SmtpSettings(id=1)
    if payload.smtp_server is not None:
        row.smtp_server = payload.smtp_server
    if payload.smtp_port is not None:
        row.smtp_port = payload.smtp_port
    if payload.smtp_user is not None:
        row.smtp_user = payload.smtp_user
    if payload.smtp_password:  # only update if non-empty
        row.smtp_password = payload.smtp_password
    if payload.smtp_bcc is not None:
        row.smtp_bcc = payload.smtp_bcc
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    logger.info("smtp_settings_updated", extra={"user": row.smtp_user})
    return {"message": "SMTP settings saved"}


# ────────────── CLI Entrypoint ──────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
