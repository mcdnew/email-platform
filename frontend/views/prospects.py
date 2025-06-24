### frontend/views/prospects.py
# This Streamlit page manages prospects.
# Uses Ag-Grid for scalable viewing/editing with export, column toggle, pagination, CRUD, and sequence assignment.

import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

API_URL = "http://localhost:8000"

def show():
    st.title("Prospects")

    # Add Prospect
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
                    st.experimental_rerun()
                else:
                    st.error("Failed to add prospect.")
            else:
                st.error("Name and Email required.")

    # CSV Import
    st.subheader("📥 Import from CSV")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df_csv = pd.read_csv(uploaded_file)
        if not {"name", "email"}.issubset(df_csv.columns):
            st.error("CSV must contain at least 'name' and 'email'.")
        else:
            if st.button("Import CSV to DB"):
                imported, failed = 0, []
                for _, row in df_csv.iterrows():
                    payload = row.to_dict()
                    resp = requests.post(f"{API_URL}/prospects", json=payload)
                    if resp.status_code == 200:
                        imported += 1
                    else:
                        failed.append(payload)
                st.success(f"Imported {imported} prospects.")
                if failed:
                    st.warning(f"{len(failed)} failed")
                    st.dataframe(pd.DataFrame(failed))

    # Filters & Sorting
    st.subheader("📋 All Prospects")
    with st.expander("🔍 Filters & Sorting"):
        search_name = st.text_input("Search by Name")
        search_email = st.text_input("Search by Email")
        search_company = st.text_input("Search by Company")
        sort_by = st.selectbox("Sort by", ["created_at", "name", "email"])
        sort_order = st.radio("Order", ["asc", "desc"], horizontal=True)

    # Fetch prospects
    params = {
        "search_name": search_name,
        "search_email": search_email,
        "search_company": search_company,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "offset": 0,
        "limit": 1000
    }
    resp = requests.get(f"{API_URL}/prospects", params=params)
    if resp.status_code != 200:
        st.error("Failed to fetch prospects")
        return
    data = resp.json()

    # Map sequence names
    seq_ids = list({p.get("sequence_id") for p in data if p.get("sequence_id")})
    seq_map = {}
    for sid in seq_ids:
        r = requests.get(f"{API_URL}/sequences/{sid}")
        if r.ok:
            seq_map[sid] = r.json().get("name")
    for p in data:
        p["sequence_name"] = seq_map.get(p.get("sequence_id"), "-")

    # Create DataFrame
    df = pd.DataFrame(data)
    if df.empty:
        st.info("No prospects found.")
        return

    # Configure Ag-Grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_side_bar()  # enable sidebar for column toggle & filters
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_default_column(editable=True)
    gb.configure_column("sequence_name", header_name="Sequence", editable=False)
    gb.configure_column("id", hide=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        height=450,
        fit_columns_on_grid_load=True
    )

    # Extract selection (list of dicts) and edited data
    selected_rows = grid_response.get("selected_rows")
    if isinstance(selected_rows, pd.DataFrame):
        selected = selected_rows.to_dict("records")
    elif selected_rows is None:
        selected = []
    else:
        selected = selected_rows

    edited_data = grid_response.get("data")
    if isinstance(edited_data, pd.DataFrame):
        edited = edited_data.to_dict("records")
    elif edited_data is None:
        edited = []
    else:
        edited = edited_data

    # Download: Selected or filtered
    if selected:
        df_export = pd.DataFrame(selected)
        st.download_button(
            label="⬇️ Download Selected Prospects",
            data=df_export.to_csv(index=False),
            file_name="selected_prospects.csv",
            mime="text/csv"
        )
    else:
        df_export = pd.DataFrame(edited)
        st.download_button(
            label="⬇️ Download All Filtered Prospects",
            data=df_export.to_csv(index=False),
            file_name="filtered_prospects.csv",
            mime="text/csv"
        )

    # ... [unchanged code above] ...

    # Save edits
    if st.button("💾 Save Changes"):
        for row in edited:
            requests.put(f"{API_URL}/prospects/{row['id']}", json=row)
        st.success("Changes saved")
        st.rerun()

    # Actions on selected rows
    if selected:
        st.markdown(f"**{len(selected)} prospect(s) selected**")
        col1, col2 = st.columns(2)
        with col1:
            seq_id = st.number_input("Assign Sequence ID", min_value=1)
            if st.button("Assign Sequence"):
                ids = [r['id'] for r in selected]
                r = requests.post(f"{API_URL}/assign-sequence", json={"prospect_ids": ids, "sequence_id": seq_id})
                if r.ok:
                    st.success("Assigned successfully")
                    st.rerun()
                else:
                    st.error("Assignment failed")
        with col2:
            if st.button("❌ Delete Selected"):
                deleted = 0
                for r in selected:
                    dr = requests.delete(f"{API_URL}/prospects/{r['id']}")
                    if dr.ok:
                        deleted += 1
                st.warning(f"Deleted {deleted} prospect(s)")
                st.rerun()

