import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

API_URL = "http://localhost:8000"

STATUS_COLORS = {
    "scheduled": "🟦 Scheduled",
    "sent": "🟩 Sent",
    "failed": "🟥 Failed",
    "in_progress": "🟧 In Progress",
    "completed": "⬜️ Completed"
}

def status_pretty(status):
    return STATUS_COLORS.get(status, status.capitalize() if status else "-")

@st.cache_data(ttl=60)
def fetch_sequences():
    resp = requests.get(f"{API_URL}/sequences")
    return resp.json() if resp.ok else []

def fetch_sequence_map(ids, all_sequences):
    return {s["id"]: s["name"] for s in all_sequences if s["id"] in ids}

def fetch_status_and_progress(prospects):
    statuses = []
    progresses = []
    progress_texts = []
    for p in prospects:
        seq_id = p.get("sequence_id")
        step_cur = p.get("sequence_step_current", 0) or 0
        step_total = p.get("sequence_steps_total", 0) or 0
        if seq_id and step_total == 0:
            statuses.append("in_progress")
        elif seq_id and step_cur == step_total and step_total > 0:
            statuses.append("completed")
        elif seq_id:
            statuses.append("in_progress")
        else:
            statuses.append("-")
        pct = int((step_cur / step_total) * 100) if step_total else 0
        progresses.append(pct)
        progress_texts.append(f"{step_cur}/{step_total}" if step_total else "-")
    return statuses, progresses, progress_texts

REAL_PROSPECT_FIELDS = {"id", "name", "email", "company", "title", "sequence_id"}

def clean_row(row):
    result = {}
    for k in REAL_PROSPECT_FIELDS:
        v = row.get(k)
        if v is not None and not (isinstance(v, float) and (pd.isna(v) or v == float('inf') or v == float('-inf'))):
            result[k] = v
    return result

def show():
    st.title("Prospects")

    # --- Fetch sequences for dropdowns
    sequences = fetch_sequences()
    seq_name_to_id = {s["name"]: s["id"] for s in sequences}
    seq_id_to_name = {s["id"]: s["name"] for s in sequences}

    # --- Add Prospect
    st.subheader("➕ Add Prospect")
    with st.form("add_prospect"):
        new_name = st.text_input("Name")
        new_email = st.text_input("Email")
        new_title = st.text_input("Title")
        new_company = st.text_input("Company")
        sequence = st.selectbox("Assign Sequence (optional)", ["(None)"] + list(seq_name_to_id.keys()))
        new_sequence_id = seq_name_to_id[sequence] if sequence != "(None)" else None

        if st.form_submit_button("Add Prospect"):
            if new_name and new_email:
                payload = {
                    "name": new_name,
                    "email": new_email,
                    "title": new_title,
                    "company": new_company,
                    "sequence_id": new_sequence_id
                }
                resp = requests.post(f"{API_URL}/prospects", json=payload)
                if resp.status_code == 200:
                    st.success("Prospect added!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to add prospect.")
            else:
                st.error("Name and Email required.")

    # --- CSV Import
    st.subheader("📥 Import from CSV")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df_csv = pd.read_csv(uploaded_file)
        st.write("Preview:", df_csv.head())
        cols = list(df_csv.columns)
        name_col = st.selectbox("Name column", cols, index=cols.index("name") if "name" in cols else 0)
        email_col = st.selectbox("Email column", cols, index=cols.index("email") if "email" in cols else 0)
        title_col = st.selectbox("Title column", ["(None)"] + cols, index=(cols.index("title") + 1) if "title" in cols else 0)
        company_col = st.selectbox("Company column", ["(None)"] + cols, index=(cols.index("company") + 1) if "company" in cols else 0)
        seq_name_col = st.selectbox("Sequence column (by name, optional)", ["(None)"] + cols, index=(cols.index("sequence") + 1) if "sequence" in cols else 0)
        seq_id_col = st.selectbox("Sequence column (by ID, optional)", ["(None)"] + cols, index=(cols.index("sequence_id") + 1) if "sequence_id" in cols else 0)

        if st.button("Import CSV to DB"):
            imported, failed = 0, []
            for _, row in df_csv.iterrows():
                payload = {
                    "name": row[name_col],
                    "email": row[email_col]
                }
                if title_col != "(None)":
                    payload["title"] = row[title_col]
                if company_col != "(None)":
                    payload["company"] = row[company_col]
                sequence_id = None
                if seq_name_col != "(None)":
                    sequence_id = seq_name_to_id.get(str(row[seq_name_col]).strip())
                elif seq_id_col != "(None)":
                    try:
                        sid = int(row[seq_id_col])
                        if sid in seq_id_to_name:
                            sequence_id = sid
                    except Exception:
                        pass
                if sequence_id:
                    payload["sequence_id"] = sequence_id
                resp = requests.post(f"{API_URL}/prospects", json=payload)
                if resp.status_code == 200:
                    imported += 1
                else:
                    failed.append(payload)
            st.success(f"Imported {imported} prospects.")
            if failed:
                st.warning(f"{len(failed)} failed")
                st.dataframe(pd.DataFrame(failed))
            st.cache_data.clear()
            st.rerun()

    # --- Filters & Sorting (manual filtering since API doesn't support it)
    st.subheader("📋 All Prospects")
    # Fetch prospects
    resp = requests.get(f"{API_URL}/prospects")
    if resp.status_code != 200:
        st.error("Failed to fetch prospects")
        return
    data = resp.json()

    # --- EMPTY DATA PROTECTION ---
    if not data or len(data) == 0:
        st.info("No prospects found. Add or import some to begin.")
        return

    # Map sequence names
    seq_ids = list({p.get("sequence_id") for p in data if p.get("sequence_id")})
    seq_map = fetch_sequence_map(seq_ids, sequences)
    for p in data:
        p["sequence_name"] = seq_map.get(p.get("sequence_id"), "-")

    # --- Status/Progress Columns ---
    status_col, progress_pcts, progress_texts = fetch_status_and_progress(data)
    for i, p in enumerate(data):
        p["status"] = status_pretty(status_col[i])
        p["progress_pct"] = progress_pcts[i]
        p["sequence_progress"] = progress_texts[i]

    # --- Ag-Grid Progress Bar JS ---
    progress_bar_js = JsCode('''
    function(params) {
        if (params.value === undefined || params.value === null || isNaN(params.value)) {
            return '';
        }
        var pct = params.value;
        var bg = pct === 100 ? '#66bb6a' : (pct > 0 ? '#ffa726' : '#e0e0e0');
        return `<div style='width:100%; background:#eee; border-radius:6px; height:18px; position:relative;'>
            <div style='background:${bg}; width:${pct}%; height:100%; border-radius:6px;'></div>
            <div style='position:absolute; left:0; top:0; width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:13px;'>${pct}%</div>
        </div>`;
    }
    ''')

    columns_to_show = [
        "id", "name", "email", "sequence_id", "sequence_name", "sequence_progress", "progress_pct", "status", "title", "company"
    ]
    df_display = pd.DataFrame(data)[[c for c in columns_to_show if c in pd.DataFrame(data).columns]]

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_side_bar()
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_default_column(editable=True)
    gb.configure_column("id", header_name="ID", editable=False)
    gb.configure_column("sequence_id", header_name="Seq ID", editable=False)
    gb.configure_column("sequence_name", header_name="Sequence", editable=False)
    gb.configure_column("sequence_progress", header_name="Progress", editable=False)
    gb.configure_column("progress_pct", header_name="Progress %", editable=False, cellRenderer=progress_bar_js)
    gb.configure_column("status", header_name="Status", editable=False)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        height=450,
        fit_columns_on_grid_load=True
    )

    # Extract selection and edited data
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

    # --- TIMELINE SIDEBAR ---
    if len(selected) == 1:
        p = selected[0]
        st.sidebar.markdown(f"### Timeline for {p['name']} (ID: {p['id']})")
        with st.spinner("Loading timeline..."):
            resp = requests.get(f"{API_URL}/prospects/{p['id']}/timeline")
            if resp.ok:
                timeline = resp.json()
                for step in timeline:
                    st.sidebar.markdown(f"""
                    **Step {step.get('step_number','')}**: {step.get('template_name','')}  
                    Subject: `{step.get('subject', '')}`  
                    Scheduled: {step.get('scheduled_at', '-')}  
                    Sent: {step.get('sent_at', '-')}  
                    Status: {STATUS_COLORS.get(step.get('status'), step.get('status'))}  
                    Opened: {step.get('opened_at', '-')}
                    """)
            else:
                st.sidebar.error("Failed to load timeline.")

    # --- BULK ACTIONS ---
    if selected:
        st.markdown(f"**Bulk Actions for {len(selected)} selected prospect(s):**")
        assign_col, clear_col, delete_col = st.columns([2, 1, 1])
        with assign_col:
            seq_options = list(seq_name_to_id.keys())
            if seq_options:
                selected_seq = st.selectbox("Assign Sequence", seq_options, key="bulk_assign_seq")
                if st.button("Assign to Sequence", key="bulk_assign_btn"):
                    seq_id = seq_name_to_id.get(selected_seq)
                    if seq_id:
                        ids = [r['id'] for r in selected]
                        r = requests.post(f"{API_URL}/assign-sequence", json={"prospect_ids": ids, "sequence_id": seq_id})
                        if r.ok:
                            st.success("Assigned successfully")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            err = r.json().get("detail", r.text) if r.content else r.text
                            st.error(f"Assignment failed: {err}")
                    else:
                        st.error("Please select a sequence.")
            else:
                st.info("No sequences available to assign.")

        with clear_col:
            if st.button("Clear Sequence", key="clear_seq_btn"):
                ids = [r['id'] for r in selected]
                for pid in ids:
                    r = requests.put(f"{API_URL}/prospects/{pid}", json={"sequence_id": None})
                st.success("Sequence cleared for selected")
                st.cache_data.clear()
                st.rerun()

        with delete_col:
            if st.button("❌ Delete Selected", key="bulk_delete_btn"):
                deleted = 0
                for r in selected:
                    dr = requests.delete(f"{API_URL}/prospects/{r['id']}")
                    if dr.ok:
                        deleted += 1
                    else:
                        try:
                            err = dr.json().get("detail", dr.text)
                        except Exception:
                            err = dr.text
                        st.error(f"Failed to delete prospect {r['id']}: {err}")
                if deleted:
                    st.warning(f"Deleted {deleted} prospect(s)")
                st.cache_data.clear()
                st.rerun()
    # --- END BULK ACTIONS ---

    # --- Download: Selected or filtered
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

    # --- Save edits
    if st.button("💾 Save Changes"):
        for row in edited:
            payload = clean_row(row)
            resp = requests.put(f"{API_URL}/prospects/{row['id']}", json=payload)
        st.success("Changes saved")
        st.cache_data.clear()
        st.rerun()

