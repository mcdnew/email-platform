### frontend/views/templates.py
# Streamlit page for managing email templates and seeing where they're used.

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

def find_usages(template_id):
    # Find which sequences/steps reference this template
    seqs = requests.get(f"{API_URL}/sequences").json()
    usages = []
    for seq in seqs:
        steps = requests.get(f"{API_URL}/sequences/{seq['id']}/steps").json()
        for step in steps:
            if step.get("template_id") == template_id:
                usages.append({
                    "sequence_id": seq["id"],
                    "sequence_name": seq["name"],
                    "step_id": step["id"],
                    "delay_days": step.get("delay_days", "?")
                })
    return usages

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

            # Show usage info:
            with st.expander("🔎 Where is this template used?"):
                usages = find_usages(t["id"])
                if usages:
                    for u in usages:
                        st.write(f"Sequence: **{u['sequence_name']}** (ID: {u['sequence_id']}), Step ID: {u['step_id']} (Delay: {u['delay_days']}d)")
                else:
                    st.info("Not used in any sequence.")

