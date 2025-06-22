# email-platform/app/utils.py

from typing import Optional
import re
from datetime import datetime

def validate_email(email: str) -> bool:
    """Simple email format validator."""
    pattern = r"[^@]+@[^@]+\.[^@]+"
    return re.match(pattern, email) is not None

def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display in the UI."""
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M")

def anonymize_email(email: str) -> str:
    """Return partially masked email address for display."""
    if "@" not in email:
        return email
    user, domain = email.split("@")
    return user[0] + "***@" + domain

