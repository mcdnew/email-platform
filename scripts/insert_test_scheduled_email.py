# 📄 File: scripts/insert_test_scheduled_email.py

from datetime import datetime, timedelta
from sqlmodel import Session

from app.database import get_session
from app.models import Prospect, EmailTemplate, ScheduledEmail

def insert_test_data():
    with next(get_session()) as session:        
        # 1. Create a test prospect
        prospect = Prospect(
            name="Test User",
            email="muntianu.claudiu@gmail.com",
            company="TestCorp"
        )
        session.add(prospect)
        session.commit()
        session.refresh(prospect)

        # 2. Create a test email template
        template = EmailTemplate(
            name="Test Template",
            subject="Scheduled Email Test",
            body="<p>Hello {{name}}, this is a scheduled email test.</p>"
        )
        session.add(template)
        session.commit()
        session.refresh(template)

        # 3. Schedule email to send immediately
        scheduled = ScheduledEmail(
            prospect_id=prospect.id,
            template_id=template.id,
            send_at=datetime.utcnow(),  # Already due
            status="pending"
        )
        session.add(scheduled)
        session.commit()

        print("✅ Test data inserted.")

if __name__ == "__main__":
    insert_test_data()

