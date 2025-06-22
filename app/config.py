# email-platform/app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_URL: str = os.getenv("DATABASE_URL", "sqlite:///./email_platform.db")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "user@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "password")
    SMTP_BCC: str = os.getenv("SMTP_BCC", "")

settings = Settings()

