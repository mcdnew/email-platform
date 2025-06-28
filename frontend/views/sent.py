import streamlit as st
import pandas as pd
import requests

API_URL = "http://localhost:8000"

def fetch_templates():
    resp = requests.get(f"{API_URL}/templates")
    return resp.json() if resp.ok else []

def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

def show():
    st.title("📬 Sent Emails Log")

    resp = requests.get(f"{API_URL}/sent-emails")
    if resp.status_code != 200:
        st.error("Failed to fetch sent emails")
        return

    data = resp.json()
    if not data:
        st.info("No emails have been sent yet.")
        return
    df = pd.DataFrame(data)
    df["sent_at"] = pd.to_datetime(df["sent_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # --- Try to map template and sequence names if IDs exist ---
    templates = fetch_templates()
    template_map = {t['id']: t['name'] for t in templates}
    sequences = fetch_sequences()
    sequence_map = {s['id']: s['name'] for s in sequences}

    if 'template_id' in df.columns:
        df["template_name"] = df["template_id"].map(template_map).fillna("")
    if 'sequence_id' in df.columns:
        df["sequence_name"] = df["sequence_id"].map(sequence_map).fillna("")

    columns_to_show = ["id", "to", "subject", "status", "sent_at"]
    if "sequence_name" in df:
        columns_to_show.append("sequence_name")
    if "template_name" in df:
        columns_to_show.append("template_name")

    st.dataframe(df[columns_to_show], use_container_width=True)

