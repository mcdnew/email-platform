### frontend/views/prospects.py
# This Streamlit page manages prospects.
# Supports CSV import, filtering, sorting, pagination, editing, deleting, manual add, assigning prospects to sequences, and shows assigned sequence and scheduled emails.

import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

def show():
    st.title("Prospects")

    st.subheader("➕ Add Prospect")
    with st.form("add_prospect"):
        new_name = st.text_input("Name")
        new_email = st.text_input("Email")
        new_title = st.text_input("Title")
        new_company = st.text_input("Company")
        if st.form_submit_button("Add Prospect"):
            if new_name and new_email:
                resp = requests.post(f"{API_URL}/prospects", json={
                    "name": new_name,
                    "email": new_email,
                    "title": new_title,
                    "company": new_company
                })
                if resp.status_code == 200:
                    st.success("Prospect added!")
                    st.rerun()
                else:
                    st.error("Failed to add prospect.")
            else:
                st.error("Name and Email required.")

    # Filters
    with st.expander("🔍 Filter & Sort"):
        search_name = st.text_input("Filter by name")
        search_email = st.text_input("Filter by email")
        search_company = st.text_input("Filter by company")
        sort_by = st.selectbox("Sort by", ["created_at", "name", "email"])
        sort_order = st.radio("Order", ["asc", "desc"], horizontal=True)

    # Pagination
    page_size = 10
    page = st.number_input("Page", min_value=1, step=1, value=1)
    offset = (page - 1) * page_size

    params = {
        "search_name": search_name,
        "search_email": search_email,
        "search_company": search_company,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "offset": offset,
        "limit": page_size
    }
    response = requests.get(f"{API_URL}/prospects", params=params)
    if response.status_code != 200:
        st.error("Failed to load prospects")
        return

    prospects = response.json()
    selected_ids = []

    for p in prospects:
        with st.expander(f"{p['name']} ({p['email']})"):
            selected = st.checkbox("Select", key=f"sel_{p['id']}")
            if selected:
                selected_ids.append(p['id'])

            st.write(f"**Title:** {p.get('title', '-')}")
            st.write(f"**Company:** {p.get('company', '-')}")
            if p.get("sequence_id"):
                st.info(f"Assigned Sequence ID: {p['sequence_id']}")
                scheduled = requests.get(f"{API_URL}/scheduled-emails/{p['id']}")
                if scheduled.status_code == 200:
                    with st.expander("🗕️ Scheduled Emails"):
                        for s in scheduled.json():
                            st.write(f"- Step {s['step_number']}: Template {s['template_id']} (Send in {s['delay_days']} days)")
            st.write(f"**Created:** {p['created_at']}")

            new_name = st.text_input("Edit Name", p["name"], key=f"edit_name_{p['id']}")
            new_email = st.text_input("Edit Email", p["email"], key=f"edit_email_{p['id']}")
            new_title = st.text_input("Edit Title", p.get("title", ""), key=f"edit_title_{p['id']}")
            new_company = st.text_input("Edit Company", p.get("company", ""), key=f"edit_company_{p['id']}")

            edit_cols = st.columns([1, 1])
            if edit_cols[0].button("Save Changes", key=f"save_{p['id']}"):
                r = requests.put(f"{API_URL}/prospects/{p['id']}", json={
                    "name": new_name,
                    "email": new_email,
                    "title": new_title,
                    "company": new_company
                })
                if r.status_code == 200:
                    st.success("Prospect updated.")
                    st.rerun()
                else:
                    st.error("Failed to update.")

            if edit_cols[1].button("Delete", key=f"del_{p['id']}"):
                r = requests.delete(f"{API_URL}/prospects/{p['id']}")
                if r.status_code == 200:
                    st.warning("Prospect deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete.")

    st.divider()
    if selected_ids:
        st.markdown(f"**Selected: {len(selected_ids)} prospect(s)**")
        sequence_id = st.number_input("Assign to Sequence ID", min_value=1)
        if st.button("Assign to Sequence"):
            result = requests.post(f"{API_URL}/assign-sequence", json={
                "prospect_ids": selected_ids,
                "sequence_id": sequence_id
            })
            if result.status_code == 200:
                st.success("Assigned to sequence!")
            else:
                st.error("Failed to assign sequence")

    st.divider()
    st.subheader("📥 Import Prospects from CSV")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        required_cols = {"name", "email"}
        if not required_cols.issubset(set(df.columns)):
            st.error("CSV must contain at least 'name' and 'email' columns.")
        else:
            imported = 0
            failed_rows = []
            if st.button("Import Prospects"):
                for i, row in df.iterrows():
                    payload = {
                        "name": row["name"],
                        "email": row["email"],
                        "title": row.get("title"),
                        "company": row.get("company")
                    }
                    response = requests.post(f"{API_URL}/prospects", json=payload)
                    if response.status_code == 200:
                        imported += 1
                    else:
                        failed_rows.append(row.to_dict())

                if imported:
                    st.success(f"Imported {imported} prospects successfully.")
                if failed_rows:
                    st.warning(f"{len(failed_rows)} rows failed to import.")
                    with st.expander("View Failed Rows"):
                        st.dataframe(pd.DataFrame(failed_rows))

