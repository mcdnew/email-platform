# frontend/views/settings.py
#
# This Streamlit “Settings” view now pulls its values directly from environment
# variables instead of importing the backend’s Python package.  That keeps the
# frontend container completely independent of backend code.

import os
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Read config from environment (with safe fall-backs)

SMTP_SERVER  = os.getenv("SMTP_SERVER",  "smtp.example.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER    = os.getenv("SMTP_USER",    "user@example.com")
# Never reveal the real SMTP password in UI
DB_URL       = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/email_platform")
# ──────────────────────────────────────────────────────────────────────────────


def show() -> None:
    """Render the Settings page."""
    st.title("Settings")

    # ─── SMTP ─────────────────────────────────────────────────────────────────
    st.subheader("SMTP Configuration")
    st.text_input("SMTP Server",  value=SMTP_SERVER,  disabled=True)
    st.number_input("SMTP Port",  value=SMTP_PORT,    disabled=True)
    st.text_input("SMTP Username", value=SMTP_USER,   disabled=True)
    st.text_input("SMTP Password", value="********",  type="password", disabled=True)

    st.info("To update SMTP settings, edit the environment variables passed to the "
            "container (or your `.env` file) and restart the application.")

    # ─── Database ─────────────────────────────────────────────────────────────
    st.subheader("Database")
    st.code(DB_URL, language="text")
    st.info("This app uses SQLModel and SQLAlchemy to manage the database.")

