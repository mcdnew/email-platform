# frontend/views/scheduled.py
# Streamlit view – no backend-code imports, talks to API via HTTP
# ------------------------------------------------------------------
import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# Backend base URL comes from env file (frontend/.env)
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Emoji tags for status column
STATUS_EMOJI = {
    "pending":   "🟧 Pending",
    "scheduled": "🟦 Scheduled",
    "sent":      "🟩 Sent",
    "failed":    "🟥 Failed",
}


# ------------------------------------------------------------------
# Helper – call backend safely
def _backend(method: str, path: str, **kwargs):
    try:
        r = requests.request(method, f"{API_URL}{path}", timeout=10, **kwargs)
        r.raise_for_status()
        return r
    except Exception as ex:
        st.error(f"Backend error: {ex}")
        return None


# ------------------------------------------------------------------
# MAIN PAGE
def show() -> None:
    st.title("Scheduled Emails Queue")

    # 1) Fetch all schedules
    r = _backend("GET", "/scheduled-emails")
    data = r.json() if r else []
    if not data:
        st.info("No scheduled emails found.")
        return

    # 2) Display table
    df = pd.DataFrame(data)
    df["send_at"] = pd.to_datetime(df["send_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df["sent_at"] = pd.to_datetime(df["sent_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df["status"] = df["status"].apply(lambda s: STATUS_EMOJI.get(s, s))

    st.dataframe(
        df[["id", "prospect_name", "prospect_email",
            "template_name", "status", "send_at", "sent_at"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Manage a Schedule")

    sid = st.number_input("Schedule ID to manage", min_value=1, step=1, value=1)
    c1, c2 = st.columns(2)

    # 3) Delete
    if c1.button("❌ Delete", key="del_sched"):
        resp = _backend("DELETE", f"/scheduled-emails/{sid}")
        if resp and resp.ok:
            st.success("Deleted ✓"); st.rerun()

    # 4) Mark as sent
    if c2.button("✅ Mark as Sent", key="mark_sent"):
        resp = _backend("POST", f"/scheduled-emails/{sid}/mark-sent")
        if resp and resp.ok:
            st.success("Marked sent ✓"); st.rerun()


# ------------------------------------------------------------------
"""
🚩  BACKEND ENDPOINTS NEEDED  (add these in app/main.py)

@app.get("/scheduled-emails")    → returns list of schedules
@app.delete("/scheduled-emails/{sid}") → delete
@app.post("/scheduled-emails/{sid}/mark-sent") → set status=sent, sent_at=now

See earlier instructions for sample implementation.
"""

