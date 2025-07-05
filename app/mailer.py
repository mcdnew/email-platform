# email-platform/app/mailer.py
# 📄 Updated to support {{placeholder}} rendering using Prospect data

import smtplib
from email.mime.text import MIMEText
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
        return text  # Fallback to original text


def send_email(
    to_email: str,
    subject: str,
    body: str,
    bcc_email: str = None,
    context: dict = None  # Prospect fields
) -> bool:
    """
    Sends an email using SMTP with optional context-based rendering.
    """
    if context:
        subject = render_template(subject, context)
        body = render_template(body, context)

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    if bcc_email:
        msg["Bcc"] = bcc_email

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()  # STARTTLS as required by Outlook 365
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False

