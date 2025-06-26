import streamlit as st
import pandas as pd
import requests

API_URL = "http://localhost:8000"

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
    st.dataframe(df[["id", "to", "subject", "status", "sent_at"]], use_container_width=True)

