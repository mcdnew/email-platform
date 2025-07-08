import streamlit as st
import requests

API_URL = "http://localhost:8000"

STEP_STATUS_COLORS = {
    "scheduled": "🟦 Scheduled",
    "sent": "🟩 Sent",
    "failed": "🟥 Failed",
    "in_progress": "🟧 In Progress",
    "completed": "⬜️ Completed"
}

@st.cache_data(ttl=60)
def fetch_templates():
    resp = requests.get(f"{API_URL}/templates")
    return resp.json() if resp.ok else []

@st.cache_data(ttl=60)
def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

def show():
    st.title("Sequences")

    # ----------- Add Sequence -----------
    st.subheader("Add Sequence")
    with st.form("add_sequence"):
        seq_name = st.text_input("Sequence Name")
        bcc_email = st.text_input("BCC Email (optional)", placeholder="one@email.com, two@email.com")
        if st.form_submit_button("Add"):
            payload = {"name": seq_name}
            if bcc_email.strip():
                payload["bcc_email"] = bcc_email.strip()
            resp = requests.post(f"{API_URL}/sequences", json=payload)
            if resp.status_code == 200:
                st.success("Sequence created")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Failed to create sequence")

    sequences = fetch_sequences()
    templates = fetch_templates()
    tmpl_name_to_id = {t['name']: t['id'] for t in templates}
    tmpl_id_to_name = {t['id']: t['name'] for t in templates}

    # ----------- Each Sequence -----------
    for seq in sequences:
        seq_key = f"expander_seq_{seq['id']}"
        expanded = st.session_state.get(seq_key, False)
        with st.expander(seq["name"] + f" (ID: {seq['id']})", expanded=expanded):
            cols = st.columns([2, 2, 1, 1])
            # Edit name and BCC
            new_name = cols[0].text_input("Edit Sequence Name", seq["name"], key=f"seqname_{seq['id']}")
            new_bcc = cols[1].text_input("BCC Email(s)", seq.get("bcc_email") or "", key=f"seqbcc_{seq['id']}", placeholder="bcc@email.com")
            if cols[2].button("Save", key=f"savename_{seq['id']}"):
                r = requests.patch(
                    f"{API_URL}/sequences/{seq['id']}", 
                    json={"name": new_name, "bcc_email": new_bcc}
                )
                if r.status_code == 200:
                    st.success("Sequence updated")
                    st.session_state[seq_key] = True
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to update sequence")
            if cols[3].button("Delete Sequence", key=f"delseq_{seq['id']}"):
                r = requests.delete(f"{API_URL}/sequences/{seq['id']}")
                if r.status_code == 200:
                    st.success("Sequence deleted")
                    st.session_state[seq_key] = False
                    st.cache_data.clear()
                    st.rerun()
                else:
                    err = r.json().get("detail", r.text) if r.content else r.text
                    st.error(f"Failed to delete sequence: {err}")

            # ----------- Steps in Sequence -----------
            step_resp = requests.get(f"{API_URL}/sequences/{seq['id']}/steps")
            if step_resp.status_code != 200:
                st.warning("No steps found.")
                continue
            steps = step_resp.json()
            if not steps:
                st.info("No steps in this sequence yet.")
            for step in steps:
                step_cols = st.columns([1, 2, 2, 1, 1])
                status = step.get("status", "scheduled")
                step_cols[0].markdown(STEP_STATUS_COLORS.get(status, status))
                delay_val = step_cols[1].number_input(
                    "Delay (days)", value=int(step["delay_days"]), min_value=0, key=f"delay_{step['id']}"
                )
                tmpl_options = ["(Select a Template)"] + list(tmpl_name_to_id.keys())
                current_tmpl_name = tmpl_id_to_name.get(step["template_id"], "(Select a Template)")
                tmpl_val = step_cols[2].selectbox(
                    "Template", tmpl_options,
                    index=tmpl_options.index(current_tmpl_name) if current_tmpl_name in tmpl_options else 0,
                    key=f"tmpl_{step['id']}"
                )
                if step_cols[3].button("Save Step", key=f"savestep_{step['id']}"):
                    if tmpl_val == "(Select a Template)":
                        st.error("Please select a template.")
                    else:
                        tmpl_id = tmpl_name_to_id[tmpl_val]
                        r = requests.patch(f"{API_URL}/sequences/steps/{step['id']}", json={
                            "delay_days": delay_val,
                            "template_id": tmpl_id
                        })
                        if r.status_code == 200:
                            st.success("Step updated")
                            st.session_state[seq_key] = True
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            err = r.json().get("detail", r.text) if r.content else r.text
                            st.error(f"Failed to update step: {err}")
                if step_cols[4].button("Delete Step", key=f"delstep_{step['id']}"):
                    r = requests.delete(f"{API_URL}/sequences/steps/{step['id']}")
                    if r.status_code == 200:
                        st.success("Step deleted")
                        st.session_state[seq_key] = True
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        err = r.json().get("detail", r.text) if r.content else r.text
                        st.error(f"Failed to delete step: {err}")

            # ----------- Add Step Form -----------
            st.markdown("**Add Step**")
            with st.form(f"add_step_{seq['id']}"):
                tmpl_names = ["(Select a Template)"] + list(tmpl_name_to_id.keys())
                tmpl_name_add = st.selectbox("Template", tmpl_names, key=f"step_tmpl_{seq['id']}")
                delay_days = st.number_input("Delay (days)", min_value=0, key=f"step_delay_{seq['id']}")
                if st.form_submit_button("Add Step"):
                    if tmpl_name_add == "(Select a Template)":
                        st.error("Please select a template.")
                    else:
                        template_id = tmpl_name_to_id[tmpl_name_add]
                        r = requests.post(f"{API_URL}/sequences/{seq['id']}/steps", json={
                            "template_id": template_id,
                            "delay_days": delay_days
                        })
                        if r.status_code == 200:
                            st.success("Step added")
                            st.session_state[seq_key] = True
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            err = r.json().get("detail", r.text) if r.content else r.text
                            st.error(f"Failed to add step: {err}")

