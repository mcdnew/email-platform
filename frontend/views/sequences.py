### frontend/views/sequences.py
# This Streamlit page allows users to manage email sequences.
# It includes sequence creation, renaming, deleting, and inline editing of steps (delay and template ID).

import streamlit as st
import requests

API_URL = "http://localhost:8000"

def show():
    st.title("Sequences")

    st.subheader("Add Sequence")
    with st.form("add_sequence"):
        seq_name = st.text_input("Sequence Name")
        if st.form_submit_button("Add"):
            resp = requests.post(f"{API_URL}/sequences", json={"name": seq_name})
            if resp.status_code == 200:
                st.success("Sequence created")
                st.rerun()
            else:
                st.error("Failed to create sequence")

    resp = requests.get(f"{API_URL}/sequences")
    if resp.status_code != 200:
        st.error("Failed to fetch sequences")
        return
    sequences = resp.json()

    for seq in sequences:
        with st.expander(seq["name"]):
            new_name = st.text_input("Edit name", seq["name"], key=f"seqname_{seq['id']}")
            cols = st.columns([1, 1])
            if cols[0].button("Save Name", key=f"savename_{seq['id']}"):
                requests.patch(f"{API_URL}/sequences/{seq['id']}", json={"name": new_name})
                st.rerun()
            if cols[1].button("Delete Sequence", key=f"delseq_{seq['id']}"):
                r = requests.delete(f"{API_URL}/sequences/{seq['id']}")
                if r.status_code == 200:
                    st.success("Sequence deleted")
                    st.rerun()
                else:
                    st.error("Failed to delete sequence")

            step_resp = requests.get(f"{API_URL}/sequences/{seq['id']}/steps")
            if step_resp.status_code != 200:
                st.warning("No steps found.")
                continue
            steps = step_resp.json()
            for step in steps:
                st.text_input("Delay (days)", value=step["delay_days"], key=f"delay_{step['id']}")
                st.text_input("Template ID", value=step["template_id"], key=f"tmpl_{step['id']}")
                edit_cols = st.columns([1, 1])
                if edit_cols[0].button("Save Step", key=f"savestep_{step['id']}"):
                    delay_val = st.session_state[f"delay_{step['id']}"]
                    tmpl_val = st.session_state[f"tmpl_{step['id']}"]
                    requests.patch(f"{API_URL}/sequences/steps/{step['id']}", json={
                        "delay_days": int(delay_val),
                        "template_id": int(tmpl_val)
                    })
                    st.success("Step updated")
                if edit_cols[1].button("Delete Step", key=f"delstep_{step['id']}"):
                    r = requests.delete(f"{API_URL}/sequences/steps/{step['id']}")
                    if r.status_code == 200:
                        st.success("Step deleted")
                        st.rerun()
                    else:
                        st.error("Failed to delete step")

            st.markdown("**Add Step**")
            with st.form(f"add_step_{seq['id']}"):
                template_id = st.number_input("Template ID", key=f"step_tmpl_{seq['id']}", min_value=1)
                delay_days = st.number_input("Delay (days)", key=f"step_delay_{seq['id']}", min_value=0)
                if st.form_submit_button("Add Step"):
                    r = requests.post(f"{API_URL}/sequences/{seq['id']}/steps", json={
                        "template_id": template_id,
                        "delay_days": delay_days
                    })
                    if r.status_code == 200:
                        st.success("Step added")
                        st.rerun()
                    else:
                        st.error("Failed to add step")

