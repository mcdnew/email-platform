# frontend/views/dev.py
import os
import streamlit as st
import requests

# API_URL = "http://localhost:8000"
API_URL = os.getenv("API_URL", "http://localhost:8000")

def show():
    st.title("⚙️ Developer Tools")

    st.markdown("## Danger Zone: Reset Database")
    st.warning(
        "This will permanently delete all prospects, templates, sequences, steps, and sent/scheduled emails. Use ONLY in development!"
    )

    if "reset_confirm" not in st.session_state:
        st.session_state.reset_confirm = False

    col1, col2 = st.columns([2, 1])
    with col2:
        confirm = st.checkbox("Yes, I am sure. Delete everything!", key="reset_confirm")

    with col1:
        if st.button("⚠️ Global Reset: Delete ALL Data"):
            if confirm:
                resp = requests.post(f"{API_URL}/reset-all")
                if resp.ok:
                    st.success("All data deleted! Refreshing page...")
                    st.rerun()
                else:
                    st.error(f"Failed to reset database: {resp.text}")
            else:
                st.error("Please check the confirmation box to proceed.")

    st.divider()

    # --- Purge/reset by table ---
    st.subheader("Clear Individual Tables")
    tables = {
        "Prospects": "prospects",
        "Templates": "templates",
        "Sequences": "sequences",
        "Sequence Steps": "sequence_steps",
        "Sent Emails": "sent_emails",
        "Scheduled Emails": "scheduled_emails",
    }
    cols = st.columns(len(tables))
    for i, (label, tbl) in enumerate(tables.items()):
        with cols[i]:
            if st.button(f"Clear {label}"):
                resp = requests.post(f"{API_URL}/dev/reset-table/{tbl}")
                if resp.ok:
                    st.success(f"{label} cleared!")
                    st.rerun()
                else:
                    st.error(f"Failed to clear {label}: {resp.text}")

    st.divider()

    # --- Bulk insert dummy/test data ---
    st.subheader("Bulk Generate Dummy/Test Data")
    colp, colt = st.columns(2)
    with colp:
        n = st.number_input("Number of Dummy Prospects", 1, 200, 10)
        if st.button("Generate Prospects"):
            resp = requests.post(f"{API_URL}/dev/generate-prospects", params={"n": n})
            if resp.ok:
                st.success(f"Added {resp.json().get('added')} prospects.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")
    with colt:
        n2 = st.number_input("Number of Dummy Templates", 1, 50, 5)
        if st.button("Generate Templates"):
            resp = requests.post(f"{API_URL}/dev/generate-templates", params={"n": n2})
            if resp.ok:
                st.success(f"Added {resp.json().get('added')} templates.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")

    st.divider()

    # --- Logging Level Toggle ---
    st.subheader("Logging Level")
    log_level = st.selectbox("Set Logging Level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    if st.button("Apply Logging Level"):
        resp = requests.post(f"{API_URL}/dev/log-level", params={"level": log_level})
        if resp.ok:
            st.success(f"Log level set to {log_level}")
        else:
            st.error(f"Failed to set log level: {resp.text}")

    st.divider()

    # --- Error Log ---
    st.subheader("Error Log")
    if st.button("Refresh Log"):
        st.rerun()
    try:
        resp = requests.get(f"{API_URL}/error-log")
        if resp.ok:
            log = resp.json().get("log", "")
            if not log.strip():
                st.success("No errors logged. All clear!")
            else:
                st.code(log, language="text")
        else:
            st.error(f"Failed to fetch log: {resp.text}")
    except Exception as ex:
        st.error(f"Error: {ex}")

    if st.button("Clear Error Log"):
        try:
            r = requests.post(f"{API_URL}/clear-error-log")
            if r.ok:
                st.success("Log cleared")
                st.rerun()
            else:
                st.error(f"Failed to clear log: {r.text}")
        except Exception as ex:
            st.error(f"Error: {ex}")

    # --- Hard Reset: Reset All + Reset IDs (Sequences) ---
    st.divider()
    st.subheader("Hard Reset (Deletes ALL & Resets IDs)")
    if st.button("🚨 Hard Reset: Delete ALL & Reset IDs"):
        resp = requests.post(f"{API_URL}/dev/reset-all-hard")
        if resp.ok:
            st.success("Hard reset completed, all data and IDs cleared!")
            st.rerun()
        else:
            st.error(f"Failed: {resp.text}")
            
            
'''    st.divider()
    st.subheader("Insert Example Test Prospect (with scheduled email)")

    if st.button("➕ Insert Test Prospect/Email"):
        resp = requests.post(f"{API_URL}/dev/insert-test-prospect")
        if resp.ok:
            st.success("Test prospect, template, and scheduled email inserted!")
            st.cache_data.clear()
            st.rerun()
        else
            st.error(f"Failed: {resp.text}")
            
'''
        

