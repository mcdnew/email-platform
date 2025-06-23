### frontend/views/templates.py
# This Streamlit page manages email templates.
# Supports creating, editing (with preview and dynamic variable support), and deleting templates.

import streamlit as st
import requests

API_URL = "http://localhost:8000"

DUMMY_DATA = {
    "name": "Alice",
    "company": "Acme Corp",
    "title": "CTO"
}

def apply_variables(text):
    for key, value in DUMMY_DATA.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text

def show():
    st.title("Email Templates")

    st.subheader("➕ Add New Template")
    with st.form("new_template"):
        name = st.text_input("Template Name")
        subject = st.text_input("Subject")
        body = st.text_area("Body (HTML supported, use {{name}}, {{company}}, etc.)")

        if st.form_submit_button("Create Template"):
            resp = requests.post(f"{API_URL}/templates", json={"name": name, "subject": subject, "body": body})
            if resp.status_code == 200:
                st.success("Template created successfully.")
                st.rerun()
            else:
                st.error("Failed to add template.")

    st.divider()
    st.subheader("All Templates")
    resp = requests.get(f"{API_URL}/templates")
    if resp.status_code != 200:
        st.error("Could not load templates.")
        return

    templates = resp.json()
    for t in templates:
        with st.expander(f"{t['name']} (ID: {t['id']})"):
            new_name = st.text_input("Edit Name", value=t["name"], key=f"name_{t['id']}")
            new_subject = st.text_input("Edit Subject", value=t["subject"], key=f"subj_{t['id']}")
            new_body = st.text_area("Edit Body (HTML supported)", value=t["body"], height=200, key=f"body_{t['id']}")

            if st.button("Preview", key=f"preview_{t['id']}"):
                st.markdown("**Preview:**", unsafe_allow_html=True)
                previewed = apply_variables(new_body)
                st.markdown(previewed, unsafe_allow_html=True)

            cols = st.columns([1, 1, 1])
            if cols[0].button("Save Changes", key=f"save_{t['id']}"):
                update = {
                    "name": new_name,
                    "subject": new_subject,
                    "body": new_body
                }
                result = requests.patch(f"{API_URL}/templates/{t['id']}", json=update)
                if result.status_code == 200:
                    st.success("Template updated.")
                    st.rerun()
                else:
                    st.error("Update failed.")

            if cols[1].button("Delete", key=f"del_{t['id']}"):
                result = requests.delete(f"{API_URL}/templates/{t['id']}")
                if result.status_code == 200:
                    st.warning("Template deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete.")

