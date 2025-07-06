### app/schemas.py
# This file defines Pydantic request & response models for FastAPI.

from pydantic import BaseModel
from typing import List, Optional

class TestEmailRequest(BaseModel):
    email: str
    subject: str
    body: str

class AssignSequenceRequest(BaseModel):
    prospect_ids: List[int]
    sequence_id: int
    ventilate_days: Optional[int] = 1
    start_date: Optional[str] = None    # NEW: for user-chosen start date

# --- New: for responses with names ---

class SentEmailRead(BaseModel):
    id: int
    to: str
    subject: str
    body: str
    sent_at: Optional[str]
    status: Optional[str]
    prospect_id: Optional[int]
    template_id: Optional[int]
    template_name: Optional[str]
    sequence_id: Optional[int]
    sequence_name: Optional[str]

    class Config:
        orm_mode = True

class ProspectRead(BaseModel):
    id: int
    name: str
    email: str
    title: Optional[str]
    company: Optional[str]
    sequence_id: Optional[int]
    sequence_name: Optional[str]

    class Config:
        orm_mode = True

