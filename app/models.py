### app/models.py
# This file defines the core SQLModel database models and CRUD-related schemas.
# Models correspond to database tables for prospects, templates, sequences, steps, and emails.

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Prospect(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    name: str
    email: str
    company: Optional[str] = None
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    unsubscribed: bool = Field(default=False)

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
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")  # ✅ Add this line
    send_at: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"

class SentEmail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    to: str
    subject: str
    body: str
    sent_at: datetime
    status: str  # sent, failed, opened, bounced
    prospect_id: Optional[int] = Field(default=None, foreign_key="prospect.id")
    template_id: Optional[int] = Field(default=None, foreign_key="emailtemplate.id")  # <-- ADD THIS
    sequence_id: Optional[int] = Field(default=None, foreign_key="sequence.id")      # <-- OPTIONAL: if you need sequence info

class EmailTemplateCreate(SQLModel):
    name: str
    subject: str
    body: str

class EmailTemplateUpdate(SQLModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

