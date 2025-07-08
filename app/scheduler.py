# email-platform/app/scheduler.py

from sqlmodel import select
from sqlalchemy import func
from datetime import datetime, time
import pytz

from app.database import get_session
from app.models import ScheduledEmail, Prospect, EmailTemplate, SentEmail, Sequence
from app.mailer import send_email
from app.config import settings

CET = pytz.timezone("Europe/Paris")
SEND_START = time(0, 0)
SEND_END = time(23, 59)

def is_working_day(dt: datetime) -> bool:
    return dt.weekday() < 5  # Mon-Fri

def is_within_window(dt: datetime) -> bool:
    # For production:  return SEND_START <= dt.time() <= SEND_END
    return True  # Always true for testing

def get_now_cet():
    return datetime.now(CET)

def count_sent_today(session) -> int:
    today = get_now_cet().date()
    return session.exec(
        select(func.count()).select_from(SentEmail).where(
            SentEmail.sent_at >= datetime.combine(today, time.min, tzinfo=CET),
            SentEmail.status == "sent"
        )
    ).scalar_one()

def run_scheduler():
    print("Running email scheduler...")
    with next(get_session()) as session:
        now = get_now_cet()

        if not is_working_day(now) or not is_within_window(now):
            print("Outside allowed CET window.")
            return

        sent_today = count_sent_today(session)
        if sent_today >= settings.MAX_EMAILS_PER_DAY:
            print("Daily email limit reached.")
            return

        pending_emails = session.exec(
            select(ScheduledEmail).where(
                ScheduledEmail.send_at <= now,
                ScheduledEmail.sent_at.is_(None),
                ScheduledEmail.status == "pending"
            )
        ).all()

        processed = 0
        for email in pending_emails:
            if sent_today >= settings.MAX_EMAILS_PER_DAY:
                print("Reached limit mid-batch.")
                break

            prospect = session.get(Prospect, email.prospect_id)
            template = session.get(EmailTemplate, email.template_id)
            sequence = session.get(Sequence, getattr(email, 'sequence_id', None)) if getattr(email, 'sequence_id', None) else None

            if not prospect or not template:
                continue

            context = {
                "name": prospect.name,
                "email": prospect.email,
                "company": prospect.company or "",
                "title": prospect.title or ""
            }

            # Determine BCC email (if any)
            bcc_email = getattr(sequence, "bcc_email", None) or getattr(settings, "DEFAULT_BCC_EMAIL", None)

            success = send_email(
                to_email=prospect.email,
                subject=template.subject,
                body=template.body,
                bcc_email=bcc_email,
                context=context
            )

            email.sent_at = datetime.utcnow()
            email.status = "sent" if success else "failed"

            sent_record = SentEmail(
                to=prospect.email,
                subject=template.subject,
                body=template.body,
                sent_at=email.sent_at,
                status=email.status,
                prospect_id=prospect.id,
                template_id=template.id,
                sequence_id=getattr(email, 'sequence_id', None),
            )

            session.add(email)
            session.add(sent_record)
            sent_today += 1 if success else 0
            processed += 1

        session.commit()
        print(f"Done. Processed: {processed}")

