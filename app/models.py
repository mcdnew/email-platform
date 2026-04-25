### app/models.py
# This file defines the current and transitional SQLModel database models.
# It still serves the existing email-platform, while incrementally adding
# the canonical platform concepts needed for the larger migration.

from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from datetime import datetime

class Prospect(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email", name="uq_prospect_email"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    name: str
    email: str
    company: Optional[str] = None
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    unsubscribed: bool = Field(default=False)
    lifecycle_stage: str = Field(default="captured", index=True)
    source_type: str = Field(default="manual", index=True)
    source_ref: Optional[str] = None
    owner: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    interested_at: Optional[datetime] = None
    qualified_at: Optional[datetime] = None

    # Business card fields
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    tags: Optional[str] = None           # JSON array stored as string e.g. '["fordaq","personal"]'
    notes: Optional[str] = None
    voice_notes: Optional[str] = None    # JSON array: [{"text": "...", "recorded_at": "..."}]
    card_image_path: Optional[str] = None
    scanned_at: Optional[datetime] = None

class EmailTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    subject: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Sequence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    bcc_email: Optional[str] = None  # <-- Per-sequence BCC email (optional)
    
class SequenceStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sequence_id: int = Field(foreign_key="sequence.id")
    template_id: int = Field(foreign_key="emailtemplate.id")
    delay_days: int
    
class ScheduledEmail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: int = Field(foreign_key="prospect.id")
    template_id: int = Field(foreign_key="emailtemplate.id")
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")
    send_at: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"
    retry_count: int = Field(default=0)

class SentEmail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    to: str
    subject: str
    body: str
    sent_at: datetime
    status: str  # sent, failed, opened, bounced
    prospect_id: Optional[int] = Field(default=None, foreign_key="prospect.id")
    template_id: Optional[int] = Field(default=None, foreign_key="emailtemplate.id")
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")
    click_count: int = Field(default=0)

class SmtpSettings(SQLModel, table=True):
    """Singleton row (id=1) that overrides env-based SMTP config when present."""
    id: int = Field(default=1, primary_key=True)
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_bcc: Optional[str] = None
    updated_at: Optional[datetime] = None


class Enrollment(SQLModel, table=True):
    """Canonical sequence membership record for acquisition and nurture flows."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: int = Field(foreign_key="prospect.id")
    sequence_id: int = Field(foreign_key="sequence.id")
    campaign_key: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="draft", index=True)
    current_step: int = Field(default=0)
    entered_at: datetime = Field(default_factory=datetime.utcnow)
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_reason: Optional[str] = None


class Suppression(SQLModel, table=True):
    """Unified suppression/do-not-contact record."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: Optional[int] = Field(default=None, foreign_key="prospect.id")
    email: Optional[str] = Field(default=None, index=True)
    scope: str = Field(default="global", index=True)
    reason: str = Field(default="manual")
    channel: Optional[str] = None
    campaign_key: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ActivityEvent(SQLModel, table=True):
    """Unified timeline/event log across capture, acquisition, and nurture."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: Optional[int] = Field(default=None, foreign_key="prospect.id")
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")
    campaign_key: Optional[str] = None
    event_type: str = Field(index=True)
    source_module: str = Field(index=True)
    payload_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(SQLModel, table=True):
    """Thread-level conversation record, especially for Gmail-backed outreach."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: int = Field(foreign_key="prospect.id")
    campaign_key: Optional[str] = Field(default=None, index=True)
    channel: str = Field(default="smtp")
    provider_thread_id: Optional[str] = Field(default=None, index=True)
    state: str = Field(default="open", index=True)
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None


class Asset(SQLModel, table=True):
    """Canonical uploaded-file metadata record."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: int = Field(foreign_key="prospect.id")
    asset_type: str = Field(index=True)
    storage_backend: str = Field(default="local")
    storage_path: str
    content_type: Optional[str] = None
    original_filename: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LeadCapture(SQLModel, table=True):
    """Raw inbound capture/discovery payload before full normalization."""

    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: Optional[int] = Field(default=None, foreign_key="prospect.id")
    source_type: str = Field(index=True)
    review_status: str = Field(default="pending_review", index=True)
    raw_payload_json: Optional[str] = None
    normalized_payload_json: Optional[str] = None
    external_ref: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None


class WorkerCampaignSnapshot(SQLModel, table=True):
    """Cached worker campaign definition and runtime summary mirrored into the core platform."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    product: Optional[str] = None
    language: Optional[str] = None
    discover_prompt: Optional[str] = None
    discover_count: Optional[int] = None
    approval_required: bool = Field(default=True)
    active: int = Field(default=0)
    interested: int = Field(default=0)
    emails_sent: int = Field(default=0)
    running: bool = Field(default=False)
    started: Optional[str] = None
    error: Optional[str] = None
    config_json: Optional[str] = None
    stats_json: Optional[str] = None
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class EmailTemplateUpdate(SQLModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
