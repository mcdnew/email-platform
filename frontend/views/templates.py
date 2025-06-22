import streamlit as st
from sqlmodel import select
from app.database import get_session
from app.models import EmailTemplate

def show():
    st.title("Email Templates")

    st.subheader("Add New Template")
    with st.form("add_template"):
        name = st.text_input("Template Name")
        subject = st.text_input("Subject")
        body = st.text_area("Body")
        submitted = st.form_submit_button("Add Template")
        if submitted:
            if name and subject and body:
                with next(get_session()) as session:
                    new = EmailTemplate(name=name, subject=subject, body=body)
                    session.add(new)
                    session.commit()
                    st.success("Template added successfully!")
                    st.rerun()
            else:
                st.error("All fields required.")

    st.divider()
    st.subheader("All Templates")

    with next(get_session()) as session:
        templates = session.exec(select(EmailTemplate)).all()

    for t in templates:
        with st.expander(f"📄 {t.name}"):
            new_subject = st.text_input("Subject", t.subject, key=f"subject_{t.id}")
            new_body = st.text_area("Body", t.body, key=f"body_{t.id}")

            cols = st.columns([1, 1])
            if cols[0].button("Save", key=f"save_{t.id}"):
                with next(get_session()) as session:
                    template = session.get(EmailTemplate, t.id)
                    template.subject = new_subject
                    template.body = new_body
                    session.add(template)
                    session.commit()
                    st.success("Template updated.")
                    st.rerun()

            if cols[1].button("Delete", key=f"delete_{t.id}"):
                with next(get_session()) as session:
                    template = session.get(EmailTemplate, t.id)
                    session.delete(template)
                    session.commit()
                    st.warning("Template deleted.")
                    st.rerun()

