# frontend/views/dashboard.py

import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

API_URL = os.getenv("API_URL", "http://localhost:8000")

@st.cache_data(ttl=60)
def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_templates():
    resp = requests.get(f"{API_URL}/templates")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_sent_emails():
    resp = requests.get(f"{API_URL}/sent-emails")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_cron_log():
    """Call backend `/cron-log` and return the last 10 'Cron job fired' lines."""
    resp = requests.get(f"{API_URL}/cron-log")
    if resp.status_code == 404:
        raise FileNotFoundError("Cron log not found on server.")
    resp.raise_for_status()
    return resp.json().get("lines", [])

def show_cron_status():
    st.subheader("⏱ Cron Job Monitor")
    try:
        lines = fetch_cron_log()
    except FileNotFoundError:
        st.error("Cron log file not found on server.")
        return
    except Exception as e:
        st.error(f"Error fetching cron log: {e}")
        return

    if not lines:
        st.warning("No cron executions recorded yet.")
        return

    # parse last timestamp from the log lines
    last_ts = lines[-1].split("]")[0].strip("[")
    try:
        dt_last = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")
        dt_next = dt_last + timedelta(minutes=5)
        st.success(f"Last run: {dt_last.strftime('%Y-%m-%d %H:%M:%S')}")
        st.info(f"Next est. run: {dt_next.strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption(f"📈 Total cron executions logged: {len(lines)}")
    except Exception as e:
        st.error(f"Error parsing cron log timestamp: {e}")

def show():
    st.title("📊 Email Platform Dashboard")

    # Cron monitor
    show_cron_status()

    # Analytics summary
    resp = requests.get(f"{API_URL}/analytics/summary")
    if resp.status_code != 200:
        st.error("Failed to load analytics")
        return
    data = resp.json()

    col1, col2, col3 = st.columns(3)
    col1.metric("📨 Emails Sent", data["total_sent"])
    col2.metric("📬 Open Rate", f"{data['open_rate']}%")
    col3.metric("❌ Failed Sends", data["total_failed"])
    st.metric("📅 Sent Today", data["sent_today"])

    st.divider()
    st.subheader("📈 Volume by Sequence & Template")

    sent_emails = fetch_sent_emails()
    seqs = fetch_sequences()
    tmpls = fetch_templates()
    seq_map = {s['id']: s['name'] for s in seqs}
    tmpl_map = {t['id']: t['name'] for t in tmpls}

    if sent_emails:
        df = pd.DataFrame(sent_emails)
        if 'sequence_id' in df.columns:
            df['sequence_name'] = df['sequence_id'].map(seq_map).fillna('')
        if 'template_id' in df.columns:
            df['template_name'] = df['template_id'].map(tmpl_map).fillna('')

        st.markdown("#### Emails Sent by Sequence")
        if 'sequence_name' in df:
            seq_grp = df.groupby('sequence_name').size().reset_index(name='count')
            st.bar_chart(seq_grp.set_index('sequence_name'))

        st.markdown("#### Emails Sent by Template")
        if 'template_name' in df:
            tmpl_grp = df.groupby('template_name').size().reset_index(name='count')
            st.bar_chart(tmpl_grp.set_index('template_name'))

    st.divider()
    st.subheader("🕒 Recent Deliveries")
    if not data["recent"]:
        st.info("No recent emails.")
    else:
        df = pd.DataFrame(data["recent"])
        df["sent_at"] = pd.to_datetime(df["sent_at"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df[["to", "subject", "status", "sent_at"]], use_container_width=True)

    st.divider()
    st.subheader("📬 Manual Scheduler Trigger")
    if st.button("📬 Run Scheduler Now"):
        run_resp = requests.post(f"{API_URL}/run-scheduler")
        if run_resp.ok:
            st.success(run_resp.json().get("message"))
        else:
            st.error("Failed to run scheduler.")

    if st.button("🚨 Force Send All Pending Emails (ignores limits!)"):
        run_resp = requests.post(f"{API_URL}/force-scheduler")
        if run_resp.ok:
            st.success(run_resp.json().get("message"))
        else:
            st.error("Force scheduler failed.")

