### frontend/views/templates.py
# This Streamlit page manages email templates.
# Supports viewing, creating, editing, and deleting templates.

import streamlit as st
import requests

API_URL = "http://localhost:8000"

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
                r = requests.post(f"{API_URL}/templates", json={
                    "name": name,
                    "subject": subject,
                    "body": body
                })
                if r.status_code == 200:
                    st.success("Template added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add template.")
            else:
                st.error("All fields required.")

    st.divider()
    st.subheader("All Templates")

    resp = requests.get(f"{API_URL}/templates")
    if resp.status_code != 200:
        st.error("Could not load templates.")
        return

    templates = resp.json()
    for t in templates:
        with st.expander(f"📄 {t['name']}"):
            new_subject = st.text_input("Subject", t["subject"], key=f"subject_{t['id']}")
            new_body = st.text_area("Body", t["body"], key=f"body_{t['id']}")
            cols = st.columns([1, 1])
            if cols[0].button("Save", key=f"save_{t['id']}"):
                r = requests.put(f"{API_URL}/templates/{t['id']}", json={
                    "subject": new_subject,
                    "body": new_body
                })
                if r.status_code == 200:
                    st.success("Template updated.")
                    st.rerun()
                else:
                    st.error("Update failed.")

            if cols[1].button("Delete", key=f"delete_{t['id']}"):
                r = requests.delete(f"{API_URL}/templates/{t['id']}")
                if r.status_code == 200:
                    st.warning("Template deleted.")
                    st.rerun()
                else:
                    st.error("Deletion failed.")
