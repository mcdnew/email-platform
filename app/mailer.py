# email-platform/app/mailer.py
# 📄 Supports multipart/alternative emails with Jinja2 {{placeholders}}

import smtplib
import html2text
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template, StrictUndefined
from jinja2.exceptions import UndefinedError

from app.config import settings


def render_template(text: str, context: dict) -> str:
    """
    Replace {{placeholders}} using Jinja2 and prospect context.
    """
    try:
        template = Template(text, undefined=StrictUndefined)
        return template.render(**context)
    except UndefinedError as e:
        print(f"⚠️ Template rendering error: {e}")
        return text  # fallback


def send_email(
    to_email: str,
    subject: str,
    body: str,
    bcc_email: str = None,
    context: dict = None
) -> bool:
    """
    Sends multipart/alternative email using SMTP. Renders body via Jinja2 if context is provided.
    Includes both plain-text and HTML versions.
    """
    # Jinja2 rendering
    if context:
        subject = render_template(subject, context)
        body = render_template(body, context)

    # Convert HTML body to plain text
    plain_text = html2text.html2text(body)

    # Build message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    if bcc_email:
        msg["Bcc"] = bcc_email

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False

