import os
import streamlit as st
import streamlit.components.v1 as components
import requests
import re
from jinja2 import Template

# API_URL = "http://localhost:8000"
API_URL = os.getenv("API_URL", "http://localhost:8000")

FALLBACK_DATA = {
    "name": "there",
    "email": "friend@example.com",
    "company": "your company",
    "title": "team lead"
}

ALLOWED_VARS = set(FALLBACK_DATA.keys())

@st.cache_data(ttl=60)
def fetch_prospects():
    resp = requests.get(f"{API_URL}/prospects")
    return resp.json() if resp.ok else []

def build_context(prospect):
    if not prospect:
        return FALLBACK_DATA
    return {
        "name": prospect.get("name") or FALLBACK_DATA["name"],
        "email": prospect.get("email") or FALLBACK_DATA["email"],
        "company": prospect.get("company") or FALLBACK_DATA["company"],
        "title": prospect.get("title") or FALLBACK_DATA["title"]
    }

def render_with_context(template_text, context):
    try:
        return Template(template_text).render(**context)
    except Exception as e:
        return f"<p style='color:red;'>⚠️ Template error: {e}</p>"

def extract_placeholders(text):
    return set(re.findall(r"{{\s*(\w+)", text))

@st.cache_data(ttl=60)
def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_steps(sequence_id):
    resp = requests.get(f"{API_URL}/sequences/{sequence_id}/steps")
    return resp.json() if resp.ok else []

def find_usages(template_id):
    seqs = fetch_sequences()
    usages = []
    for seq in seqs:
        steps = fetch_steps(seq['id'])
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
    st.title("📨 Email Templates")

    prospects = fetch_prospects()
    prospect_names = [f"{p['name']} <{p['email']}>" for p in prospects]
    selected_idx = st.selectbox("Choose a prospect for preview rendering", ["(Dummy data)"] + prospect_names)
    selected_prospect = None if selected_idx == "(Dummy data)" else prospects[prospect_names.index(selected_idx) - 1]
    context = build_context(selected_prospect)

    with st.expander("🧩 Available Template Variables", expanded=True):
        st.markdown("""
        - `{{ name }}` → Prospect's full name  
        - `{{ email }}` → Prospect's email  
        - `{{ company }}` → Company name  
        - `{{ title }}` → Job title  
        Use fallbacks with `| default("fallback")`, e.g. `{{ name | default("there") }}`  
        """)

    st.subheader("➕ Add New Template")
    with st.form("new_template"):
        name = st.text_input("Template Name")
        subject = st.text_input("Subject (supports {{...}})")
        body = st.text_area("Body (HTML + {{...}})", height=300)

        if st.form_submit_button("Create Template"):
            if not name or not subject or not body:
                st.warning("All fields are required.")
            else:
                payload = {"name": name, "subject": subject, "body": body}
                resp = requests.post(f"{API_URL}/templates", json=payload)
                if resp.status_code == 200:
                    st.success("Template created.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Failed to create template: {resp.text}")

    st.divider()
    st.subheader("📄 All Templates")

    resp = requests.get(f"{API_URL}/templates")
    if not resp.ok:
        st.error("Failed to load templates.")
        return

    templates = resp.json()
    for t in templates:
        t_key = f"expander_tmpl_{t['id']}"
        expanded = st.session_state.get(t_key, False)
        with st.expander(f"{t['name']} (ID: {t['id']})", expanded=expanded):
            new_name = st.text_input("Edit Name", value=t["name"], key=f"name_{t['id']}")
            new_subject = st.text_input("Edit Subject", value=t["subject"], key=f"subj_{t['id']}")
            new_body = st.text_area("Edit Body", value=t["body"], height=220, key=f"body_{t['id']}")

            used_vars = extract_placeholders(new_body + new_subject)
            invalid_vars = used_vars - ALLOWED_VARS
            if invalid_vars:
                st.warning(f"Unknown placeholders used: {', '.join(invalid_vars)}")

            st.markdown("**Subject Preview:**")
            rendered_subject = render_with_context(new_subject, context)
            st.code(rendered_subject, language="text")

            st.markdown("**Body Preview (Text):**")
            # Strip HTML tags for text version
            import re
            plain_text = re.sub(r'<[^>]*>', '', render_with_context(new_body, context))
            st.code(plain_text, language="text")

            st.markdown("**Body Preview (HTML):**", unsafe_allow_html=True)
            rendered_body = render_with_context(new_body, context)
            components.html(rendered_body, height=500, scrolling=True)

            # Always show Send Test section
            st.markdown("#### ✉️ Send Test Email")
            test_email = st.text_input("Your email address", key=f"test_email_{t['id']}")
            if st.button("🚀 Send Test", key=f"test_btn_{t['id']}"):
                if not test_email or "@" not in test_email:
                    st.error("Please enter a valid email address.")
                elif not rendered_subject or not rendered_body:
                    st.error("Subject and body must not be empty.")
                else:
                    payload = {
                        "email": test_email,
                        "subject": rendered_subject,
                        "body": rendered_body
                    }
                    try:
                        r = requests.post(f"{API_URL}/send-test", json=payload)
                        if r.status_code == 200:
                            st.success("Test email sent!")
                        else:
                            try:
                                err_detail = r.json().get("detail", r.text)
                            except Exception:
                                err_detail = r.text
                            st.error(f"Failed to send test: {err_detail}")
                    except Exception as e:
                        st.error(f"Error connecting to backend: {e}")

            cols = st.columns([1, 1, 1])
            if cols[0].button("💾 Save Changes", key=f"save_{t['id']}"):
                update = {
                    "name": new_name,
                    "subject": new_subject,
                    "body": new_body
                }
                result = requests.patch(f"{API_URL}/templates/{t['id']}", json=update)
                if result.status_code == 200:
                    st.success("Template updated.")
                    st.session_state[t_key] = True
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Update failed.")

            if cols[1].button("❌ Delete", key=f"del_{t['id']}"):
                result = requests.delete(f"{API_URL}/templates/{t['id']}")
                if result.status_code == 200:
                    st.warning("Template deleted.")
                    st.session_state[t_key] = False
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to delete.")

            with st.expander("🔎 Where is this template used?"):
                usages = find_usages(t["id"])
                if usages:
                    for u in usages:
                        st.markdown(
                            f"- Sequence **{u['sequence_name']}** (ID: `{u['sequence_id']}`), Step ID: `{u['step_id']}`, Delay: {u['delay_days']}d"
                        )
                else:
                    st.info("Not used in any sequences.")

