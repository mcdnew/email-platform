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

    # ── API Auth ─────────────────────────────────────────────────────────────────
    # Secret key for X-API-Key header auth on all endpoints.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    API_KEY: str = os.getenv("API_KEY", "")

    # ── Unsubscribe Token Secret ──────────────────────────────────────────────────
    # Dedicated secret for signing unsubscribe tokens (itsdangerous URLSafeSerializer).
    # Keeping this separate from API_KEY means rotating API_KEY does not invalidate
    # unsubscribe links already embedded in sent emails.
    # Falls back to API_KEY if unset (backward compat).
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    UNSUBSCRIBE_SECRET: str = os.getenv("UNSUBSCRIBE_SECRET", "")

    # ── Scheduler / Send Window ──────────────────────────────────────────────────
    # Timezone for send window enforcement (pytz timezone string).
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")

    # ── Retry Logic ──────────────────────────────────────────────────────────────
    # Maximum number of times a failed email will be retried via POST /retry-failed.
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 3))

    # ── Logging ───────────────────────────────────────────────────────────────────
    # Log level for app.* loggers (DEBUG / INFO / WARNING / ERROR).
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    # File path for the JSON log (also served by GET /error-log in DEV_MODE).
    LOG_PATH: str = os.getenv("LOG_PATH", "error_log.txt")

# Instantiate a single settings object to import elsewhere
settings = Settings()

