import os
import streamlit as st
import pandas as pd
import requests


# API_URL = "http://localhost:8000"
API_URL = os.getenv("API_URL", "http://localhost:8000")
# Status color/emoji tags for sent emails
STATUS_COLORS = {
    "scheduled":   "🟦 Scheduled",
    "sent":        "🟩 Sent",
    "failed":      "🟥 Failed",
    "opened":      "🟦 Opened",
    "in_sequence": "🟧 In Sequence",
    "completed":   "⬜️ Completed"
}

@st.cache_data(ttl=60)
def fetch_templates():
    resp = requests.get(f"{API_URL}/templates")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_sent_emails():
    resp = requests.get(f"{API_URL}/sent-emails")
    return resp.json() if resp.ok else []

def show():
    st.title("📬 Sent Emails Log")

    data = fetch_sent_emails()
    if not data:
        st.info("No emails have been sent yet.")
        return

    df = pd.DataFrame(data)
    df["sent_at"] = pd.to_datetime(df["sent_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Map template and sequence names if IDs exist
    templates = fetch_templates()
    template_map = {t["id"]: t["name"] for t in templates}
    sequences = fetch_sequences()
    sequence_map = {s["id"]: s["name"] for s in sequences}

    if "template_id" in df.columns:
        df["template_name"] = df["template_id"].map(template_map).fillna("")
    if "sequence_id" in df.columns:
        df["sequence_name"] = df["sequence_id"].map(sequence_map).fillna("")

    # Status with color/emoji
    def status_tag(row):
        status = str(row.get("status", "")).lower()
        return STATUS_COLORS.get(status, status.capitalize())

    df["status_tag"] = df.apply(status_tag, axis=1)

    columns_to_show = ["id", "to", "subject", "status_tag", "sent_at"]
    if "sequence_name" in df.columns:
        columns_to_show.append("sequence_name")
    if "template_name" in df.columns:
        columns_to_show.append("template_name")

    st.dataframe(df[columns_to_show], use_container_width=True)

    # Clear All Sent Emails (uses dev endpoint)
    st.divider()
    st.subheader("Danger: Clear All Sent Emails")
    if st.button("❌ Clear All Sent Emails"):
        resp = requests.post(f"{API_URL}/dev/reset-table/sent_emails")
        if resp.ok:
            st.success("All sent emails deleted!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Delete failed: {resp.text}")

