# email-platform/app/models.py

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Prospect(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    name: str
    email: str
    company: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

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

class SequenceStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sequence_id: int = Field(foreign_key="sequence.id")
    template_id: int = Field(foreign_key="emailtemplate.id")
    delay_days: int  # number of days after previous step

class ScheduledEmail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prospect_id: int = Field(foreign_key="prospect.id")
    template_id: int = Field(foreign_key="emailtemplate.id")
    send_at: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, failed

