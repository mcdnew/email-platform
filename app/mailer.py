# email-platform/app/mailer.py
import smtplib
from email.message import EmailMessage
from app.config import settings

def send_email(to_email, subject, body, bcc_email=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email

    if bcc_email:
        msg["Bcc"] = bcc_email

    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

