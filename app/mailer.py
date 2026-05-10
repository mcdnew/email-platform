# email-platform/app/mailer.py
# Supports multipart/alternative emails with Jinja2 {{placeholders}} and open tracking.

import logging
import os
import re
import smtplib
import html2text
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote
from jinja2 import Template, StrictUndefined
from jinja2.exceptions import UndefinedError

from app.config import settings

logger = logging.getLogger(__name__)

# Base URL for tracking pixel — set TRACKING_BASE_URL in .env (e.g. https://yourdomain.com)
TRACKING_BASE_URL = os.getenv("TRACKING_BASE_URL", "").rstrip("/")


def render_template(text: str, context: dict) -> str:
    """Replace {{placeholders}} using Jinja2 and prospect context."""
    try:
        template = Template(text, undefined=StrictUndefined)
        return template.render(**context)
    except UndefinedError as e:
        logger.warning("template_render_error", extra={"error": str(e)})
        return text  # fallback to raw body


def send_email(
    to_email: str,
    subject: str,
    body: str,
    bcc_email: str = None,
    context: dict = None,
    email_id: int = None,
    smtp_override: dict = None,
) -> bool:
    """
    Send a multipart/alternative email via SMTP.

    - Renders Jinja2 placeholders if context is provided.
    - Appends an open-tracking pixel if email_id is given and TRACKING_BASE_URL is set.
    - Returns True on success, False on any SMTP failure.

    Flow when called from the scheduler:
      1. SentEmail row is pre-inserted with status='sending' to get its ID.
      2. That ID is passed here as email_id.
      3. The tracking pixel src points to /track_open?email_id=<id>.
      4. Caller updates SentEmail status to 'sent' or 'failed' after this returns.
    """
    if context:
        subject = render_template(subject, context)
        body = render_template(body, context)

    # Rewrite links and append open-tracking pixel
    if email_id and TRACKING_BASE_URL:
        def rewrite_link(match: re.Match) -> str:
            original_url = match.group(1)
            # Don't rewrite mailto: or already-rewritten tracking links
            if original_url.startswith("mailto:") or "/track_click" in original_url:
                return match.group(0)
            encoded = quote(original_url, safe="")
            tracked = f"{TRACKING_BASE_URL}/track_click?email_id={email_id}&url={encoded}"
            return f'href="{tracked}"'

        body = re.sub(r'href="([^"]+)"', rewrite_link, body)

        pixel = (
            f'<img src="{TRACKING_BASE_URL}/track_open?email_id={email_id}" '
            f'width="1" height="1" alt="" style="display:none;" />'
        )
        body = body + pixel

    plain_text = html2text.html2text(body)

    cfg = smtp_override or {}
    smtp_server = cfg.get("smtp_server") or settings.SMTP_SERVER
    smtp_port = cfg.get("smtp_port") or settings.SMTP_PORT
    smtp_user = cfg.get("smtp_user") or settings.SMTP_USER
    smtp_password = cfg.get("smtp_password") or settings.SMTP_PASSWORD

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user or os.getenv("MAIL_FROM", "noreply@localhost")
    msg["To"] = to_email
    if bcc_email:
        msg["Bcc"] = bcc_email

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if smtp_user:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return "sent"
    except smtplib.SMTPRecipientsRefused as e:
        logger.error("smtp_bounce", extra={"to": to_email, "error": str(e)})
        return "bounced"
    except smtplib.SMTPDataError as e:
        # 5xx permanent failures are bounces; 4xx are transient
        code = e.smtp_code if hasattr(e, "smtp_code") else 0
        status = "bounced" if code >= 500 else "failed"
        logger.error("smtp_data_error", extra={"to": to_email, "code": code, "error": str(e)})
        return status
    except Exception as e:
        logger.error("smtp_failure", extra={"to": to_email, "error": str(e)}, exc_info=e)
        return "failed"
