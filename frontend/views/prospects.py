import streamlit as st
import pandas as pd
import requests
import datetime
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
    tab1, tab2 = st.tabs(["🆕 New Prospects", "📋 Active Prospects"])

    # ---- Tab 1: New Prospects (sequence_id is None) ----
    with tab1:
        st.subheader("➕ Add Prospect")
        sequences = fetch_sequences()
        seq_name_to_id = {s["name"]: s["id"] for s in sequences}
        seq_id_to_name = {s["id"]: s["name"] for s in sequences}

        with st.form("add_prospect_new"):
            new_name = st.text_input("Name", key="new_name_new")
            new_email = st.text_input("Email", key="new_email_new")
            new_title = st.text_input("Title", key="new_title_new")
            new_company = st.text_input("Company", key="new_company_new")
            if st.form_submit_button("Add Prospect"):
                if new_name and new_email:
                    payload = {
                        "name": new_name,
                        "email": new_email,
                        "title": new_title,
                        "company": new_company
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

        st.subheader("📥 Import from CSV")
        uploaded_file = st.file_uploader("Upload CSV (New)", type=["csv"], key="fileuploader_new")
        if uploaded_file:
            df_csv = pd.read_csv(uploaded_file)
            st.write("Preview:", df_csv.head())
            cols = list(df_csv.columns)
            name_col = st.selectbox("Name column", cols, index=cols.index("name") if "name" in cols else 0, key="name_col_new")
            email_col = st.selectbox("Email column", cols, index=cols.index("email") if "email" in cols else 0, key="email_col_new")
            title_col = st.selectbox("Title column", ["(None)"] + cols, index=(cols.index("title") + 1) if "title" in cols else 0, key="title_col_new")
            company_col = st.selectbox("Company column", ["(None)"] + cols, index=(cols.index("company") + 1) if "company" in cols else 0, key="company_col_new")
            if st.button("Import CSV to New Prospects"):
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

        st.subheader("🆕 New Prospects Table (Unassigned)")
        resp = requests.get(f"{API_URL}/prospects", params={"assigned": False})
        new_prospects = resp.json() if resp.ok else []
        if not new_prospects:
            st.info("No new prospects. Import or add some!")
            return
        df = pd.DataFrame(new_prospects)
        if not df.empty:
            select_all = st.checkbox("Select ALL new prospects", value=False)
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection("multiple", use_checkbox=True)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)
            grid_options = gb.build()
            grid_response = AgGrid(
                df, gridOptions=grid_options, update_mode=GridUpdateMode.SELECTION_CHANGED,
                enable_enterprise_modules=True, height=400
            )
            _selected = grid_response.get("selected_rows")
            if isinstance(_selected, pd.DataFrame):
                selected = _selected.to_dict("records")
            elif _selected is None:
                selected = []
            else:
                selected = _selected

            if select_all:
                selected = df.to_dict("records")
            st.write(f"{len(selected)} selected")

            assign_col, delete_col = st.columns([2, 1])
            with assign_col:
                seq_options = list(seq_name_to_id.keys())
                selected_seq = st.selectbox("Assign Sequence", seq_options, key="assign_seq_new")
                # --- Start Date and Ventilate Days Inputs ---
                start_date = st.date_input(
                    "Start date for first email",
                    value=datetime.date.today(),
                    min_value=datetime.date.today(),
                    key="start_date"
                )
                ventilate_days = st.number_input(
                    "Distribute 1st email over N days",
                    min_value=1, max_value=365, value=7, step=1, key="ventilate_days"
                )
                assign_disabled = len(selected) == 0
                if st.button("Assign Sequence to Selected", key="assign_btn_new", disabled=assign_disabled):
                    seq_id = seq_name_to_id.get(selected_seq)
                    ids = [r['id'] for r in selected]
                    payload = {
                        "prospect_ids": ids,
                        "sequence_id": seq_id,
                        "ventilate_days": ventilate_days,
                        "start_date": str(start_date)
                    }
                    resp = requests.post(f"{API_URL}/assign-sequence", json=payload)
                    if resp.ok:
                        st.success("Assigned. Refreshing…")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to assign.")

            with delete_col:
                delete_disabled = len(selected) == 0
                if st.button("Delete Selected", key="delete_btn_new", disabled=delete_disabled):
                    for r in selected:
                        requests.delete(f"{API_URL}/prospects/{r['id']}")
                    st.success("Deleted selected.")
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.info("No new prospects.")

    # ---- Tab 2: Active Prospects (sequence_id is not None) ----
    with tab2:
        st.title("Prospects")
        sequences = fetch_sequences()
        seq_name_to_id = {s["name"]: s["id"] for s in sequences}
        seq_id_to_name = {s["id"]: s["name"] for s in sequences}

        st.subheader("📋 All Prospects (Assigned)")
        resp = requests.get(f"{API_URL}/prospects", params={"assigned": True})
        if resp.status_code != 200:
            st.error("Failed to fetch prospects")
            return
        data = resp.json()

        if not data or len(data) == 0:
            st.info("No prospects found. Add or import some to begin.")
            return

        seq_ids = list({p.get("sequence_id") for p in data if p.get("sequence_id")})
        seq_map = fetch_sequence_map(seq_ids, sequences)
        for p in data:
            p["sequence_name"] = seq_map.get(p.get("sequence_id"), "-")

        status_col, progress_pcts, progress_texts = fetch_status_and_progress(data)
        for i, p in enumerate(data):
            p["status"] = status_pretty(status_col[i])
            p["progress_pct"] = progress_pcts[i]
            p["sequence_progress"] = progress_texts[i]

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

        _selected = grid_response.get("selected_rows")
        if isinstance(_selected, pd.DataFrame):
            selected = _selected.to_dict("records")
        elif _selected is None:
            selected = []
        else:
            selected = _selected

        edited_data = grid_response.get("data")
        if isinstance(edited_data, pd.DataFrame):
            edited = edited_data.to_dict("records")
        elif edited_data is None:
            edited = []
        else:
            edited = edited_data

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

        if st.button("💾 Save Changes"):
            for row in edited:
                payload = clean_row(row)
                resp = requests.put(f"{API_URL}/prospects/{row['id']}", json=payload)
            st.success("Changes saved")
            st.cache_data.clear()
            st.rerun()

