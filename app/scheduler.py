# email-platform/app/scheduler.py

from sqlmodel import select
from datetime import datetime
from app.database import get_session
from app.models import ScheduledEmail, Prospect, EmailTemplate
from app.mailer import send_email

def run_scheduler():
    print("Running email scheduler...")
    with next(get_session()) as session:
        now = datetime.utcnow()
        pending_emails = session.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.send_at <= now,
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending"
            )
        ).all()

        for email in pending_emails:
            prospect = session.get(Prospect, email.prospect_id)
            template = session.get(EmailTemplate, email.template_id)
            if not prospect or not template:
                continue

            success = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=prospect.email if '@example.com' not in prospect.email else None  # Optional BCC logic
            )

            if success:
                email.status = "sent"
                email.sent_at = datetime.utcnow()
            else:
                email.status = "failed"

            session.add(email)

        session.commit()
        print("Done.")


