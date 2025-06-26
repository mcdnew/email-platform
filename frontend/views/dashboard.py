# email-platform/frontend/views/dashboard.py
# 📄 File: frontend/views/dashboard.py

import streamlit as st
import pandas as pd
import requests

API_URL = "http://localhost:8000"

def show():
    st.title("📊 Email Platform Dashboard")

    # Fetch analytics
    resp = requests.get(f"{API_URL}/analytics/summary")
    if resp.status_code != 200:
        st.error("Failed to load analytics")
        return

    data = resp.json()

    # Layout for metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("📨 Emails Sent", data["total_sent"])
    col2.metric("📬 Open Rate", f"{data['open_rate']}%")
    col3.metric("❌ Failed Sends", data["total_failed"])

    st.metric("📅 Sent Today", data["sent_today"])

    st.divider()

    st.subheader("🕒 Recent Deliveries")
    if not data["recent"]:
        st.info("No recent emails.")
    else:
        df = pd.DataFrame(data["recent"])
        df["sent_at"] = pd.to_datetime(df["sent_at"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df[["to", "subject", "status", "sent_at"]], use_container_width=True)

    # Run scheduler manually
    st.divider()
    st.subheader("📬 Manual Scheduler Trigger")
    if st.button("📬 Run Scheduler Now"):
        run_resp = requests.post(f"{API_URL}/run-scheduler")
        if run_resp.ok:
            st.success(run_resp.json().get("message"))
        else:
            st.error("Failed to run scheduler.")


