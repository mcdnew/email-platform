#v frontend/views/scheduled.py

import streamlit as st
from datetime import datetime
from app.database import get_session
from app.models import ScheduledEmail, Prospect, EmailTemplate
from app.utils import format_datetime, anonymize_email
from sqlmodel import select


def show():
    st.title("Scheduled Emails Queue")

    session = next(get_session())

    stmt = select(ScheduledEmail)
    scheduled_emails = session.exec(stmt).all()

    if not scheduled_emails:
        st.info("No scheduled emails found.")
        return

    for email in scheduled_emails:
        prospect = session.get(Prospect, email.prospect_id)
        template = session.get(EmailTemplate, email.template_id)

        with st.expander(f"Email to {prospect.name} ({email.status})"):
            st.write(f"**Email:** {anonymize_email(prospect.email)}")
            st.write(f"**Send At:** {format_datetime(email.send_at)}")
            st.write(f"**Sent At:** {format_datetime(email.sent_at)}")
            st.write(f"**Template:** {template.name if template else 'Unknown'}")

            cols = st.columns(2)
            if cols[0].button("Delete", key=f"delete_{email.id}"):
                session.delete(email)
                session.commit()
                st.success("Deleted.")
                st.experimental_rerun()

            if cols[1].button("Mark as Sent", key=f"sent_{email.id}"):
                email.status = "sent"
                email.sent_at = datetime.now()
                session.add(email)
                session.commit()
                st.success("Marked as sent.")
                st.experimental_rerun()

