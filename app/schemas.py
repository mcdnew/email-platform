### app/schemas.py
# This file defines Pydantic request models used in API routes.
# These are not persisted to the database and exist solely for validation of incoming JSON payloads.

from pydantic import BaseModel
from typing import List

class TestEmailRequest(BaseModel):
    email: str
    subject: str
    body: str

class AssignSequenceRequest(BaseModel):
    prospect_ids: List[int]
    sequence_id: int
