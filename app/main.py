# 📄 app/main.py  – full, fixed with BCC support & SQLAlchemy-2 helper  (2025-07-07)

import os, logging
from datetime import datetime, date, time
from typing import List, Optional

import pytz
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from sqlmodel import Session, select
from sqlalchemy import func

from app.database import get_session
from app.models import (
    Prospect, EmailTemplate, Sequence, SequenceStep,
    ScheduledEmail, SentEmail,
)
from app.schemas import AssignSequenceRequest, SequenceCreate, SequenceRead, TestEmailRequest
from app.mailer import send_email
from app.config import settings
from app import crud
from app.routes import open_tracking
from app.dev import router as dev_router

# ────────────── App & Routers ──────────────
app = FastAPI()
app.include_router(open_tracking.router)
app.include_router(dev_router)

# ────────────── Constants ──────────────
CET        = pytz.timezone("Europe/Paris")
SEND_START = time(0, 0)
SEND_END   = time(23, 59)
LOG_PATH   = "error_log.txt"

# ────────────── Error Logging ──────────────
elog = logging.getLogger("error_logger")
elog.setLevel(logging.ERROR)
if not elog.handlers:
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    elog.addHandler(fh)

@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    elog.error("URL: %s METHOD: %s\n%r", request.url, request.method, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})

@app.get("/error-log")
def get_error_log():
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    if not os.path.exists(LOG_PATH):
        return {"log": ""}
    with open(LOG_PATH) as f:
        return {"log": f.read()}

@app.post("/clear-error-log")
def clear_error_log():
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    open(LOG_PATH, "w").close()
    return {"message": "Error log cleared"}

# ────────────── Helpers ──────────────
def _now() -> datetime:
    return datetime.now(CET)

def _is_working(d: datetime) -> bool:
    return d.weekday() < 5

def _scalar(db: Session, stmt) -> int:
    """
    Execute stmt and return single int (0 if none),
    works whether .one_or_none() yields (5,) or 5 or None.
    """
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

count_sent_today = _sent_today

# ────────────── Scheduler ──────────────
def _send_pending() -> str:
    with next(get_session()) as db:
        now = _now()
        if not (_is_working(now) and SEND_START <= now.time() <= SEND_END):
            return "outside window"

        sent_today = _sent_today(db)
        if sent_today >= settings.MAX_EMAILS_PER_DAY:
            return "daily limit reached"

        pending = db.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.send_at <= now,
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending",
            )
        ).all()

        processed = 0
        for sched in pending:
            if sent_today >= settings.MAX_EMAILS_PER_DAY:
                break

            prospect = db.get(Prospect, sched.prospect_id)
            template = db.get(EmailTemplate, sched.template_id)

            # Skip if essential data missing
            if not (prospect and template):
                continue

            # Sequence (optional)
            seq = db.get(Sequence, sched.sequence_id) if sched.sequence_id else None
            bcc = getattr(seq, "bcc_email", None) or None  # Only use if defined

            ctx = {
                "name":    prospect.name,
                "email":   prospect.email,
                "company": prospect.company or "",
                "title":   prospect.title or "",
            }

            ok = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=bcc,
                context=ctx,
            )

            sched.sent_at = datetime.utcnow()
            sched.status  = "sent" if ok else "failed"
            db.add(SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=sched.sent_at,
                status=sched.status,
                prospect_id=prospect.id,
                template_id=template.id,
                sequence_id=sched.sequence_id,
            ))
            processed += 1
            sent_today += int(ok)

        db.commit()
        return f"processed {processed}"

@app.post("/run-scheduler")
def run_scheduler_api():
    return {"message": _send_pending()}
    
#-----------------------------------

@app.post("/force-scheduler")
def force_scheduler():
    with next(get_session()) as db:
        now = datetime.utcnow()
        pending = db.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending",
                ScheduledEmail.send_at <= now  # ← only overdue
            )
        ).all()

        processed = 0
        for sched in pending:
            prospect = db.get(Prospect, sched.prospect_id)
            template = db.get(EmailTemplate, sched.template_id)
            if not (prospect and template):
                continue

            sequence = db.get(Sequence, prospect.sequence_id) if prospect.sequence_id else None

            ctx = {
                "name":    prospect.name,
                "email":   prospect.email,
                "company": prospect.company or "",
                "title":   prospect.title or "",
            }

            bcc = getattr(sequence, "bcc_email", None) or getattr(settings, "DEFAULT_BCC_EMAIL", "")

            ok = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=bcc,
                context=ctx,
            )

            sched.sent_at = datetime.utcnow()
            sched.status  = "sent" if ok else "failed"

            db.add(SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=sched.sent_at,
                status=sched.status,
                prospect_id=prospect.id,
                template_id=template.id,
                sequence_id=prospect.sequence_id  # now safe
            ))
            db.add(sched)
            processed += 1

        db.commit()
        return {"message": f"FORCE scheduler sent {processed} overdue emails"}
    

# ────────────── Prospects CRUD/List ──────────────
@app.get("/prospects")
def list_prospects(
    assigned: Optional[str] = None,
    db: Session = Depends(get_session),
):
    if assigned is not None:
        assigned = str(assigned).lower() in {"1", "true", "yes", "on"}

    q = select(Prospect)
    if assigned is True:
        q = q.where(Prospect.sequence_id.is_not(None))
    elif assigned is False:
        q = q.where(Prospect.sequence_id.is_(None))
    prospects = db.exec(q).all()

    steps_per_seq = {
        seq.id: _scalar(
            db,
            select(func.count()).select_from(SequenceStep)
            .where(SequenceStep.sequence_id == seq.id)
        )
        for seq in db.exec(select(Sequence)).all()
    }

    sched_map = {}
    for s in db.exec(select(ScheduledEmail)).all():
        sched_map.setdefault(s.prospect_id, []).append(s)

    out = []
    for p in prospects:
        total = steps_per_seq.get(p.sequence_id, 0)
        done  = sum(1 for s in sched_map.get(p.id, []) if s.status in {"sent", "failed"})
        out.append({
            **p.dict(),
            "sequence_name": db.get(Sequence, p.sequence_id).name if p.sequence_id else None,
            "sequence_steps_total": total,
            "sequence_step_current": done,
            "sequence_progress_pct": int(100 * done / total) if total else 0,
        })
    return out

@app.post("/prospects")
def add_prospect(p: Prospect, db: Session = Depends(get_session)):
    return crud.create_prospect(db, p)

@app.put("/prospects/{pid}")
def edit_prospect(pid: int, data: Prospect, db: Session = Depends(get_session)):
    obj = db.get(Prospect, pid)
    if not obj:
        raise HTTPException(404, "Prospect not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    return crud.update_prospect(db, obj)

@app.delete("/prospects/{pid}")
def delete_prospect(pid: int, db: Session = Depends(get_session)):
    if not crud.delete_prospect(db, pid):
        raise HTTPException(404, "Prospect not found")
    return {"message": "deleted"}

# ────────────── Assign Sequence / Bulk Scheduling ──────────────
@app.post("/assign-sequence")
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
@app.get("/sequences", response_model=List[SequenceRead])
def list_sequences(db: Session = Depends(get_session)):
    return db.exec(select(Sequence)).all()

@app.post("/sequences", response_model=SequenceRead)
def create_sequence(data: SequenceCreate, db: Session = Depends(get_session)):
    obj = Sequence(**data.dict()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.patch("/sequences/{sid}", response_model=SequenceRead)
def update_sequence(sid: int, data: SequenceCreate, db: Session = Depends(get_session)):
    obj = db.get(Sequence, sid)
    if not obj: raise HTTPException(404, "Sequence not found")
    for k, v in data.dict(exclude_unset=True).items(): setattr(obj, k, v)
    db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/sequences/{sid}")
def delete_sequence(sid: int, db: Session = Depends(get_session)):
    obj = db.get(Sequence, sid)
    if not obj: raise HTTPException(404, "Sequence not found")
    db.delete(obj); db.commit(); return {"message": "deleted"}

@app.get("/sequences/{sid}/steps")
def list_steps(sid: int, db: Session = Depends(get_session)):
    return crud.get_sequence_steps(db, sid)

@app.post("/sequences/{sid}/steps")
def add_step(sid: int, step: SequenceStep, db: Session = Depends(get_session)):
    if not db.get(Sequence, sid): raise HTTPException(400, "Sequence not exist")
    if not db.get(EmailTemplate, step.template_id): raise HTTPException(400, "Template not exist")
    step.sequence_id = sid
    return crud.create_sequence_step(db, step)

@app.patch("/sequences/steps/{step_id}")
def edit_step(step_id: int, data: SequenceStep, db: Session = Depends(get_session)):
    res = crud.update_sequence_step(db, step_id, data)
    if res is None: raise HTTPException(404, "Step not found")
    return res

@app.delete("/sequences/steps/{step_id}")
def delete_step(step_id: int, db: Session = Depends(get_session)):
    if not crud.delete_sequence_step(db, step_id): raise HTTPException(404, "Step not found")
    return {"message": "deleted"}

# ────────────── Templates CRUD ──────────────
@app.get("/templates")
def list_templates(db: Session = Depends(get_session)):
    return crud.get_templates(db)

@app.post("/templates")
def create_template(t: EmailTemplate, db: Session = Depends(get_session)):
    return crud.create_template(db, t)

@app.patch("/templates/{tid}")
def update_template(tid: int, data: EmailTemplate, db: Session = Depends(get_session)):
    tpl = db.get(EmailTemplate, tid)
    if not tpl: raise HTTPException(404, "Template not found")
    for k, v in data.dict(exclude_unset=True).items(): setattr(tpl, k, v)
    return crud.update_template(db, tid, data)

@app.delete("/templates/{tid}")
def delete_template(tid: int, db: Session = Depends(get_session)):
    res = crud.delete_template(db, tid)
    if res is None: raise HTTPException(400, "Template used in step")
    if res is False: raise HTTPException(404, "Template not found")
    return {"message": "deleted"}

# ────────────── Sent Emails & Analytics ──────────────
@app.get("/sent-emails")
def list_sent(db: Session = Depends(get_session)):
    sent = db.exec(select(SentEmail).order_by(SentEmail.sent_at.desc())).all()
    tnames = {t.id: t.name for t in db.exec(select(EmailTemplate)).all()}
    snames = {s.id: s.name for s in db.exec(select(Sequence)).all()}
    enriched = []
    for e in sent:
        enriched.append({
            **e.dict(),
            "template_name": tnames.get(e.template_id),
            "sequence_name": snames.get(e.sequence_id),
        })
    return enriched

@app.get("/analytics/summary")
def analytics(db: Session = Depends(get_session)):
    all_sent = db.exec(select(SentEmail)).all()
    failed   = sum(1 for e in all_sent if e.status == "failed")
    opened   = sum(1 for e in all_sent if e.status == "opened")
    return {
        "total_sent": len(all_sent),
        "total_failed": failed,
        "open_rate": round(opened / len(all_sent) * 100, 2) if all_sent else 0,
        "sent_today": _sent_today(db),
        "recent": [
            {
                "to": e.to,
                "subject": e.subject,
                "status": e.status,
                "sent_at": e.sent_at,
                "template_name": getattr(e, 'template_name', None),
                "sequence_name": getattr(e, 'sequence_name', None)
            } for e in all_sent[:10]
        ]
    }

'''@app.post("/send-test")
def send_test_email(data: TestEmailRequest):
    ok = send_email(
        to_email=data.email,
        subject=data.subject,
        body=data.body,
        bcc_email=getattr(settings, "DEFAULT_BCC_EMAIL", ""),
    )
    if not ok:
        raise HTTPException(500, "SMTP failed")
    return {"message": "sent"}
'''


@app.post("/send-test")
def send_test_email(data: TestEmailRequest):
    context = {
        "name": "Test Name",
        "title": "Test Title",
        "company": "Test Company",
        "email": data.email,
    }

    ok = send_email(
        to_email=data.email,
        subject=data.subject,
        body=data.body,
        bcc_email=getattr(settings, "DEFAULT_BCC_EMAIL", ""),
        context=context,  # make sure it gets rendered properly
    )
    if not ok:
        raise HTTPException(500, "SMTP failed")
    return {"message": "sent"}



@app.get("/prospects/{pid}/timeline")
def timeline(pid: int, db: Session = Depends(get_session)):
    prospect = db.get(Prospect, pid)
    if not prospect:
        raise HTTPException(404, "Prospect not found")
    sched = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == pid)).all()
    tmpl  = {t.id: t for t in db.exec(select(EmailTemplate)).all()}
    if prospect.sequence_id:
        steps = db.exec(
            select(SequenceStep)
            .where(SequenceStep.sequence_id == prospect.sequence_id)
            .order_by(SequenceStep.delay_days)
        ).all()
        tl = []
        for idx, step in enumerate(steps, 1):
            match = next((s for s in sched if s.template_id == step.template_id), None)
            et = tmpl.get(step.template_id)
            tl.append({
                "step_number": idx,
                "template_name": et.name if et else "-",
                "subject": et.subject if et else "",
                "scheduled_at": getattr(match, "send_at", None),
                "sent_at":      getattr(match, "sent_at", None),
                "status":       getattr(match, "status", "-") if match else "-",
                "opened_at":    getattr(match, "opened_at", None) if match else None,
            })
        return tl
    return sorted([{
        "step_number": None,
        "template_name": tmpl.get(s.template_id).name if tmpl.get(s.template_id) else "-",
        "subject": tmpl.get(s.template_id).subject if tmpl.get(s.template_id) else "",
        "scheduled_at": s.send_at,
        "sent_at": s.sent_at,
        "status": s.status,
        "opened_at": getattr(s, "opened_at", None),
    } for s in sched], key=lambda x: x["scheduled_at"] or datetime.min)

@app.get("/unsubscribe")
def unsubscribe(token: str, db: Session = Depends(get_session)):
    from app.tracking import serializer
    try:
        email = serializer.loads(token)
        prospect = db.exec(select(Prospect).where(Prospect.email == email)).first()
        if prospect:
            prospect.unsubscribed = True
            db.add(prospect); db.commit()
        return HTMLResponse("<h3>You’ve been unsubscribed.</h3>")
    except:
        return HTMLResponse("<h3>Invalid or expired link.</h3>", status_code=400)

@app.post("/reset-all", status_code=status.HTTP_200_OK)
def reset_all(db: Session = Depends(get_session)):
    if os.getenv("DEV_MODE", "false").lower() != "true":
        raise HTTPException(403, "Not allowed in production")
    for model in (SentEmail, ScheduledEmail, SequenceStep, Sequence, Prospect, EmailTemplate):
        db.query(model).delete()
        db.commit()
    return {"message": "all data deleted"}

# ────────────── CLI Entrypoint ──────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

