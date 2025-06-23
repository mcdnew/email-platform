# scripts/seed_db.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session
from app.database import engine
from app.models import Prospect, EmailTemplate, Sequence, SequenceStep

with Session(engine) as session:
    # Add templates
    template1 = EmailTemplate(name="Welcome", subject="Welcome to our product", body="<p>Hi there!</p>")
    template2 = EmailTemplate(name="Follow-up", subject="Just checking in", body="<p>Hope you're well!</p>")
    session.add_all([template1, template2])
    session.commit()
    session.refresh(template1)
    session.refresh(template2)

    # Add sequence
    sequence = Sequence(name="Onboarding Sequence")
    session.add(sequence)
    session.commit()
    session.refresh(sequence)

    step1 = SequenceStep(sequence_id=sequence.id, template_id=template1.id, delay_days=0)
    step2 = SequenceStep(sequence_id=sequence.id, template_id=template2.id, delay_days=3)
    session.add_all([step1, step2])

    # Add prospects
    prospects = [
        Prospect(name="Alice Smith", email="alice@example.com", title="CEO", company="Alpha Inc"),
        Prospect(name="Bob Johnson", email="bob@example.com", title="CTO", company="Beta LLC"),
        Prospect(name="Carol White", email="carol@example.com", title="CMO", company="Gamma Corp"),
        Prospect(name="David Black", email="david@example.com", title="CFO", company="Delta Ltd"),
        Prospect(name="Eve Green", email="eve@example.com", title="COO", company="Epsilon SA"),
    ]
    session.add_all(prospects)
    session.commit()

    print("✅ Seeded database with dummy data.")

