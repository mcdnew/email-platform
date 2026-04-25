### app/schemas.py
# Pydantic request & response models for FastAPI

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
    start_date: Optional[str] = None          # Start date for scheduling (as string)

# --- Sequence schemas (for create/read) ---

class SequenceBase(BaseModel):
    name: str
    bcc_email: Optional[str] = None

class SequenceCreate(SequenceBase):
    pass

class SequenceRead(SequenceBase):
    id: int
    created_at: Optional[datetime] = None    # Accepts datetime objects!

    class Config:
        orm_mode = True

# --- Read models for API responses ---

class SentEmailRead(BaseModel):
    id: int
    to: str
    subject: str
    body: str
    sent_at: Optional[datetime]
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

# --- Bulk prospect import (CSV → JSON array) ---
class ProspectImport(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    title: Optional[str] = None

# --- Business card upsert (from mobile app) ---
class BusinessCardUpsert(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    tags: Optional[List[str]] = None        # app sends list, we store as JSON string
    notes: Optional[str] = None
    voice_note: Optional[str] = None        # single transcription text from app
    scanned_at: Optional[str] = None        # ISO datetime string

class BusinessCardUpsertResponse(BaseModel):
    id: int
    action: str   # "created" or "updated"

# --- Sequence step reorder ---
class StepReorderItem(BaseModel):
    step_id: int
    delay_days: int

class StepReorderRequest(BaseModel):
    steps: List[StepReorderItem]


class OutreachDiscoveredLead(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None
    fact: Optional[str] = None
    external_ref: Optional[str] = None


class OutreachDiscoveryIngestRequest(BaseModel):
    campaign_key: str
    approval_required: bool = True
    leads: List[OutreachDiscoveredLead]


class OutreachDiscoveryResultItem(BaseModel):
    external_ref: Optional[str] = None
    prospect_id: Optional[int] = None
    email: Optional[str] = None
    action: str


class OutreachDiscoveryIngestResponse(BaseModel):
    created_or_updated: int
    lead_captures_recorded: int
    items: List[OutreachDiscoveryResultItem]


class OutreachMessageSentRequest(BaseModel):
    prospect_id: Optional[int] = None
    email: Optional[str] = None
    campaign_key: str
    gmail_thread_id: str
    sequence_step: int
    subject: str
    body: str
    sent_at: Optional[str] = None


class OutreachReplyIngestRequest(BaseModel):
    prospect_id: Optional[int] = None
    email: Optional[str] = None
    campaign_key: str
    intent: str
    body: str
    gmail_thread_id: Optional[str] = None
    from_email: Optional[str] = None
    incoming_message_id: Optional[str] = None
    received_at: Optional[str] = None


class OutreachNurtureHandoffRequest(BaseModel):
    prospect_id: Optional[int] = None
    email: Optional[str] = None
    campaign_key: str
    sequence_id: int
    qualified: bool = True
    start_date: Optional[str] = None
    ventilate_days: Optional[int] = 0
    notes: Optional[str] = None
