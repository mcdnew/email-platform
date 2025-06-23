### app/main.py
# This file registers all FastAPI routes for the backend API.
# It includes endpoints for handling templates, prospects, sequences, test-sending emails, and more.

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlmodel import Session, select
from typing import Optional
from app.models import EmailTemplateUpdate, EmailTemplate, EmailTemplateCreate, Prospect, Sequence
from app.schemas import TestEmailRequest, AssignSequenceRequest
from app.database import get_session
from app.crud import (
    update_template,
    create_template,
    get_templates,
    schedule_sequence_for_prospect,
    update_prospect,
    delete_prospect,
    create_prospect,
    create_sequence,
    get_sequences
)
from app.mailer import send_email

app = FastAPI()

# Sequence steps
@app.get("/sequences/{sequence_id}/steps")
def get_sequence_steps(sequence_id: int, session: Session = Depends(get_session)):
    from app.models import SequenceStep
    stmt = select(SequenceStep).where(SequenceStep.sequence_id == sequence_id)
    return session.exec(stmt).all()

@app.post("/sequences/{sequence_id}/steps")
def create_sequence_step(sequence_id: int, step: dict, session: Session = Depends(get_session)):
    from app.models import SequenceStep
    new_step = SequenceStep(sequence_id=sequence_id, **step)
    session.add(new_step)
    session.commit()
    session.refresh(new_step)
    return new_step

@app.patch("/sequences/steps/{step_id}")
def update_sequence_step(step_id: int, step_data: dict, session: Session = Depends(get_session)):
    from app.models import SequenceStep
    step = session.get(SequenceStep, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    for key, value in step_data.items():
        setattr(step, key, value)
    session.add(step)
    session.commit()
    session.refresh(step)
    return step

@app.delete("/sequences/steps/{step_id}")
def delete_sequence_step(step_id: int, session: Session = Depends(get_session)):
    from app.models import SequenceStep
    step = session.get(SequenceStep, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    session.delete(step)
    session.commit()
    return {"message": "Step deleted"}

# Prospects
@app.get("/prospects")
def get_filtered_prospects(
    search_name: Optional[str] = Query(None),
    search_email: Optional[str] = Query(None),
    search_company: Optional[str] = Query(None),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    stmt = select(Prospect)
    if search_name:
        stmt = stmt.where(Prospect.name.contains(search_name))
    if search_email:
        stmt = stmt.where(Prospect.email.contains(search_email))
    if search_company:
        stmt = stmt.where(Prospect.company.contains(search_company))
    order = getattr(getattr(Prospect, sort_by), sort_order)()
    stmt = stmt.order_by(order).offset(offset).limit(limit)
    return session.exec(stmt).all()

@app.post("/prospects")
def create_prospect_route(prospect: Prospect, session: Session = Depends(get_session)):
    return create_prospect(session, prospect)

@app.put("/prospects/{prospect_id}")
def update_prospect_route(prospect_id: int, updated: dict, session: Session = Depends(get_session)):
    prospect = session.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    for key, value in updated.items():
        setattr(prospect, key, value)
    session.add(prospect)
    session.commit()
    session.refresh(prospect)
    return prospect

@app.delete("/prospects/{prospect_id}")
def delete_prospect_route(prospect_id: int, session: Session = Depends(get_session)):
    try:
        prospect = session.get(Prospect, prospect_id)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")
        session.delete(prospect)
        session.commit()
        return {"message": "Prospect deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sequences
@app.get("/sequences")
def get_all_sequences(session: Session = Depends(get_session)):
    return get_sequences(session)

@app.post("/sequences")
def create_sequence_route(sequence: Sequence, session: Session = Depends(get_session)):
    return create_sequence(session, sequence)

@app.delete("/sequences/{sequence_id}")
def delete_sequence_route(sequence_id: int, session: Session = Depends(get_session)):
    sequence = session.get(Sequence, sequence_id)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    session.delete(sequence)
    session.commit()
    return {"message": "Sequence deleted"}

@app.post("/assign-sequence")
def assign_sequence(req: AssignSequenceRequest, session: Session = Depends(get_session)):
    for pid in req.prospect_ids:
        prospect = session.get(Prospect, pid)
        if prospect:
            prospect.sequence_id = req.sequence_id
            session.add(prospect)
            schedule_sequence_for_prospect(session, prospect_id=pid, sequence_id=req.sequence_id)
    session.commit()
    return {"message": "Sequence assigned"}

# Email templates
@app.get("/templates")
def get_all_templates(session: Session = Depends(get_session)):
    return get_templates(session)

@app.post("/templates")
def create_template_route(template: EmailTemplateCreate, session: Session = Depends(get_session)):
    return create_template(session, EmailTemplate(**template.dict()))

@app.put("/templates/{template_id}")
def update_template_route(template_id: int, template: EmailTemplateUpdate, session: Session = Depends(get_session)):
    return update_template(session, template_id, template)

@app.delete("/templates/{template_id}")
def delete_template_route(template_id: int, session: Session = Depends(get_session)):
    from app.models import EmailTemplate
    template = session.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    session.delete(template)
    session.commit()
    return {"message": "Template deleted"}

# Test email
@app.post("/send-test")
def send_test_email(payload: TestEmailRequest):
    try:
        send_email(to_address=payload.email, subject=payload.subject, html_body=payload.body)
        return {"message": "Test email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

