### app/schemas.py
# Pydantic request & response models for FastAPI

from pydantic import BaseModel
from typing import List, Optional

# --- For testing email sending ---
class TestEmailRequest(BaseModel):
    email: str
    subject: str
    body: str

# --- Assignment/bulk scheduling API ---
class AssignSequenceRequest(BaseModel):
    prospect_ids: List[int]
    sequence_id: int
    ventilate_days: Optional[int] = 1         # For randomizing spread over days
    start_date: Optional[str] = None          # NEW: Start date for scheduling

# --- Read models for API responses ---

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

