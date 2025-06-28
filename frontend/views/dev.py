# frontend/views/dev.py
import streamlit as st
import requests

API_URL = "http://localhost:8000"

def show():
    st.title("⚙️ Developer Tools")

    st.markdown("## Danger Zone: Reset Database")
    st.warning("This will permanently delete all prospects, templates, sequences, steps, and sent/scheduled emails. Use ONLY in development!")

    if "reset_confirm" not in st.session_state:
        st.session_state.reset_confirm = False

    # Use a button and a separate confirmation checkbox
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

