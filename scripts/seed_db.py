# scripts/seed_db.py

from datetime import datetime
from app.database import init_db, get_session
from app.models import Prospect, EmailTemplate, Sequence, SequenceStep
from sqlmodel import Session

def seed():
    init_db()
    with next(get_session()) as session:
        # Add prospects
        session.add_all([
            Prospect(title="Mr.", name="John Doe", email="john@example.com", company="Acme Inc."),
            Prospect(title="Ms.", name="Jane Smith", email="jane@example.com", company="Globex Corp.")
        ])

        # Add templates
        template1 = EmailTemplate(name="Intro", subject="Welcome!", body="Hello there!")
        template2 = EmailTemplate(name="Follow-up", subject="Just Checking In", body="How are things?")
        session.add_all([template1, template2])
        session.commit()

        # Add a sequence
        sequence = Sequence(name="Welcome Series")
        session.add(sequence)
        session.commit()

        # Add steps to sequence
        step1 = SequenceStep(sequence_id=sequence.id, template_id=template1.id, delay_days=0)
        step2 = SequenceStep(sequence_id=sequence.id, template_id=template2.id, delay_days=2)
        session.add_all([step1, step2])
        session.commit()

        print("✅ Seed data inserted.")

if __name__ == "__main__":
    seed()

