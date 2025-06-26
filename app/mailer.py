# email-platform/app/mailer.py
# 📄 File: app/mailer.py


import smtplib
from email.mime.text import MIMEText
from app.config import settings

def send_email(to_email: str, subject: str, body: str, bcc_email: str = None) -> bool:
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

