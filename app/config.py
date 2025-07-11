# app/config.py

"""
Email Platform Configuration

Create a `.env` file at your project root (and `frontend/.env` for the UI) containing:

# ── Database ─────────────────────────────────────────────────────────────────────
# PostgreSQL (recommended in Docker or prod):
DATABASE_URL=postgresql://<DB_USER>:<DB_PASS>@<DB_HOST>:<DB_PORT>/<DB_NAME>
# e.g.:
# DATABASE_URL=postgresql://email_user:strongpassword@db:5432/email_platform

# Fallback (if you omit DATABASE_URL): uses SQLite at ./email_platform.db
# DATABASE_URL=sqlite:///./email_platform.db

# ── SMTP (for sending emails) ───────────────────────────────────────────────────
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_username@example.com
SMTP_PASSWORD=your_smtp_password
# Optional Bcc address (comma-separated)
SMTP_BCC=manager@example.com

# ── Scheduler & Rate Limits ────────────────────────────────────────────────────
MAX_EMAILS_PER_DAY=100
# (Optional) a shared secret if you secure your scheduler endpoints
SCHEDULER_SECRET=your_scheduler_secret_token
"""

import os
from dotenv import load_dotenv

# Load any variables defined in a .env file into the environment
load_dotenv()

class Settings:
    # ── Database URL ────────────────────────────────────────────────────────────
    # Environment variable: DATABASE_URL
    # Format for Postgres:
    #   postgresql://user:password@host:port/dbname
    # If unset, falls back to SQLite at "./email_platform.db"
    DB_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./email_platform.db"
    )

    # ── SMTP Server Settings ────────────────────────────────────────────────────
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "user@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "password")
    # Optional BCC for all outgoing mail
    SMTP_BCC: str = os.getenv("SMTP_BCC", "")

    # ── Email Rate Limit ────────────────────────────────────────────────────────
    # Maximum emails sent per calendar day
    MAX_EMAILS_PER_DAY: int = int(os.getenv("MAX_EMAILS_PER_DAY", 100))

    # ── Scheduler Secret (optional) ──────────────────────────────────────────────
    # If you protect your /run-scheduler endpoint with a token,
    # define it here and check it in your FastAPI route.
    SCHEDULER_SECRET: str = os.getenv("SCHEDULER_SECRET", "")

# Instantiate a single settings object to import elsewhere
settings = Settings()

