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
    lifecycle_stage: Optional[str] = None

    class Config:
        orm_mode = True

# --- Bulk prospect import (CSV → JSON array) ---
class ProspectImport(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    title: Optional[str] = None


class ProspectUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    sequence_id: Optional[int] = None
    unsubscribed: Optional[bool] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

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


class LeadCaptureReviewRequest(BaseModel):
    review_status: str  # approved | rejected
    notes: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None


class LeadCaptureReviewResponse(BaseModel):
    message: str
    capture_id: int
    review_status: str
    prospect_id: Optional[int] = None


class LeadCaptureRead(BaseModel):
    id: int
    prospect_id: Optional[int] = None
    source_type: str
    review_status: str
    raw_payload_json: Optional[str] = None
    normalized_payload_json: Optional[str] = None
    external_ref: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class ActivityEventRead(BaseModel):
    id: int
    prospect_id: Optional[int] = None
    sequence_id: Optional[int] = None
    campaign_key: Optional[str] = None
    event_type: str
    source_module: str
    payload_json: Optional[str] = None
    created_at: datetime


class ConversationRead(BaseModel):
    id: int
    prospect_id: int
    campaign_key: Optional[str] = None
    channel: str
    provider_thread_id: Optional[str] = None
    state: str
    opened_at: datetime
    last_message_at: Optional[datetime] = None


class ProspectLifecycleActionRequest(BaseModel):
    target_stage: str
    notes: Optional[str] = None


class AcquisitionCampaignSummaryRead(BaseModel):
    campaign_key: str
    pending_review: int
    interested: int
    conversations: int
    recent_events: int


class WorkerCampaignRead(BaseModel):
    name: str
    product: str
    language: str
    discover_prompt: str
    discover_count: int
    approval_required: bool
    active: int
    interested: int
    emails_sent: int
    running: bool
    started: Optional[str] = None
    error: Optional[str] = None


class WorkerCampaignRunRequest(BaseModel):
    dry_run: bool = False


class WorkerCampaignDiscoverRequest(BaseModel):
    dry_run: bool = False
    count: Optional[int] = None


class WorkerCampaignCreateRequest(BaseModel):
    name: str
    config: dict


class WorkerCampaignDetailRead(BaseModel):
    name: str
    config: dict
    stats: dict
    running: bool
    started: Optional[str] = None
    error: Optional[str] = None


class WorkerCampaignUpdateRequest(BaseModel):
    config: dict


class WorkerCampaignActivityEntryRead(BaseModel):
    id: int
    ts: str
    campaign: Optional[str] = None
    level: str
    message: str


class WorkerCampaignActivityFeedRead(BaseModel):
    entries: List[WorkerCampaignActivityEntryRead]
    max_id: int


class WorkerCampaignTraceEntryRead(BaseModel):
    id: int
    ts: str
    campaign: str
    run_id: Optional[str] = None
    kind: str
    event: str
    payload: Optional[str] = None


class WorkerCampaignSnapshotRead(BaseModel):
    name: str
    product: Optional[str] = None
    language: Optional[str] = None
    discover_prompt: Optional[str] = None
    discover_count: Optional[int] = None
    approval_required: bool
    active: int
    interested: int
    emails_sent: int
    running: bool
    started: Optional[str] = None
    error: Optional[str] = None
    config_json: Optional[str] = None
    stats_json: Optional[str] = None
    synced_at: datetime
