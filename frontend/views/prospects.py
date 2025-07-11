import os
import datetime as _dt
import io
import csv
import pandas as pd
import requests
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# API_URL = "http://localhost:8000"
API_URL = os.getenv("API_URL", "http://localhost:8000")

STATUS = {
    "scheduled":   "🕦 Scheduled",
    "sent":        "🟩 Sent",
    "failed":      "🟥 Failed",
    "in_progress": "🟧 In Progress",
    "completed":   "⬜️ Completed",
}

def _pretty_status(key: str | None) -> str:
    return STATUS.get(key, (key or "").capitalize())

def _extract(grid_resp, key: str) -> list[dict]:
    v = grid_resp.get(key)
    if v is None:
        return []
    if isinstance(v, pd.DataFrame):
        return v.to_dict("records")
    if isinstance(v, list):
        return v
    try:
        return list(v)
    except:
        return []

@st.cache_data(ttl=60)
def _fetch_sequences() -> list[dict]:
    r = requests.get(f"{API_URL}/sequences")
    r.raise_for_status()
    return r.json()

def _parse_csv(uploaded) -> list[dict]:
    try:
        text = uploaded.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        out = []
        for row in reader:
            name    = row.get("name")    or row.get("Name")
            email   = row.get("email")   or row.get("Email")
            title   = row.get("title")   or row.get("Title", "")
            company = row.get("company") or row.get("Company", "")
            if name and email:
                out.append({"name": name, "email": email, "title": title, "company": company})
        return out
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []

def show():
    # Load sequences
    seqs = _fetch_sequences()
    name_to_id = {s["name"]: s["id"] for s in seqs}
    id_to_name = {s["id"]: s["name"] for s in seqs}

    # Choose view
    view = st.radio(
        "View:", ["🆕 New Prospects", "📋 Active Prospects"],
        horizontal=True, index=0, key="prospects_view"
    )

    # ─── New Prospects ─────────────────────────────────────────────────────────
    if view == "🆕 New Prospects":
        # Bulk CSV import
        st.subheader("📥 Bulk import from CSV")
        csv_file = st.file_uploader("Upload CSV (name,email,title,company)", type="csv", key="csv_import")
        if csv_file:
            parsed = _parse_csv(csv_file)
            st.success(f"Parsed {len(parsed)} rows.")
            if st.button("➕ Import All"):
                ok = bad = 0
                for rec in parsed:
                    try:
                        r = requests.post(f"{API_URL}/prospects", json=rec)
                        r.raise_for_status(); ok += 1
                    except: bad += 1
                st.success(f"Imported {ok}, failed {bad}")
                st.cache_data.clear(); st.rerun()

        # Add single prospect
        st.subheader("➕ Add Single Prospect")
        with st.form("add_prospect"):
            n = st.text_input("Name")
            e = st.text_input("Email")
            t = st.text_input("Title")
            c = st.text_input("Company")
            submitted = st.form_submit_button("Add")
        if submitted:
            if not (n and e): st.warning("Name & Email required")
            else:
                try:
                    r = requests.post(f"{API_URL}/prospects", json={"name":n,"email":e,"title":t,"company":c})
                    r.raise_for_status(); st.success("Prospect added"); st.cache_data.clear(); st.rerun()
                except Exception as ex:
                    st.error(f"Failed: {ex}")

        st.divider()
        st.subheader("🆕 Unassigned Prospects")
        # Fetch unassigned
        try:
            resp = requests.get(f"{API_URL}/prospects", params={"assigned":False}); resp.raise_for_status()
            unassigned = resp.json()
        except Exception as ex:
            st.error(f"Fetch error: {ex}"); unassigned = []

        df_un = pd.DataFrame(unassigned)
        if df_un.empty:
            st.info("No unassigned prospects.")
            return

        # Email search
        search = st.text_input("🔍 Search by Email", value="", key="search_email_new")
        if search:
            df_un = df_un[df_un["email"].str.contains(search, case=False, na=False)]

        # Table & selection
        sel_all = st.checkbox("Select ALL", key="new_sel_all")
        prev_ids = st.session_state.get("new_sel_ids", [])
        pre = [r for r in unassigned if r["id"] in prev_ids]
        gb = GridOptionsBuilder.from_dataframe(df_un)
        gb.configure_side_bar(); gb.configure_selection("multiple", use_checkbox=True, pre_selected_rows=pre)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=st.session_state.get("new_page_size",20))
        grid = AgGrid(df_un, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED,
                      allow_unsafe_jscode=True, enable_enterprise_modules=True, key="new_ag")
        selected = _extract(grid, "selected_rows")
        if sel_all: selected = df_un.to_dict("records")
        st.session_state["new_sel_ids"] = [r["id"] for r in selected if r.get("id")]
        st.caption(f"Selected: {len(selected)}")

        # Bulk actions
        c1, c2 = st.columns([3,1])
        with c1:
            seq_pick = st.selectbox("Sequence", list(name_to_id.keys()))
            start = st.date_input("First email date", value=_dt.date.today())
            vent = st.number_input("Spread over N days", 0,365,0)
            assign = st.button("Assign →", disabled=not selected)
        if assign:
            ids = [r["id"] for r in selected if r.get("id")]
            try:
                r2 = requests.post(f"{API_URL}/assign-sequence", json={"prospect_ids":ids,
                            "sequence_id":name_to_id[seq_pick],"ventilate_days":vent,
                            "start_date":str(start)})
                r2.raise_for_status(); st.success("Assigned ✔"); st.cache_data.clear(); st.rerun()
            except Exception as ex: st.error(f"Assign failed: {ex}")

        if selected:
            st.divider(); st.markdown(f"**Bulk actions ({len(selected)})**")
            if st.button("❌ Delete Selected Prospects"):
                for x in selected:
                    try: requests.delete(f"{API_URL}/prospects/{x['id']}")
                    except Exception as ex: st.error(f"Failed to delete ID {x['id']}: {ex}")
                st.success("Deleted ✔"); st.cache_data.clear(); st.rerun()

        st.selectbox("Rows per page (New)", [10,20,50,100],
                     index=[10,20,50,100].index(st.session_state.get("new_page_size",20)),
                     key="new_page_size")

    # ─── Active Prospects ───────────────────────────────────────────────────────
    else:
        st.subheader("📋 Active Prospects")
        try:
            resp = requests.get(f"{API_URL}/prospects", params={"assigned":True}); resp.raise_for_status()
            active = resp.json() or []
        except Exception as ex:
            st.error(f"Fetch error: {ex}"); return

        if not active:
            st.info("No active prospects yet."); return

        for p in active:
            done = p.get("sequence_step_current",0) or 0
            total = p.get("sequence_steps_total",0) or 0
            p["sequence_name"] = id_to_name.get(p.get("sequence_id"))
            p["steps"] = f"{done} / {total}"
            p["status"] = _pretty_status("completed" if done==total and total>0 else "in_progress")

        df_act = pd.DataFrame(active)
        if df_act.empty:
            st.info("No active prospects to show."); return

        search_a = st.text_input("🔍 Search by Email", value="", key="search_email_active")
        if search_a:
            df_act = df_act[df_act["email"].str.contains(search_a, case=False, na=False)]

        for col in ["sequence_steps_total","sequence_step_current","sequence_progress_pct"]:
            if col in df_act.columns: df_act.drop(columns=[col], inplace=True)

        prev2 = st.session_state.get("act_sel_ids", [])
        pre2 = [r for r in active if r["id"] in prev2]
        page_size = st.selectbox("Rows per page (Active)",[10,20,50,100],
                                 index=[10,20,50,100].index(st.session_state.get("act_page_size",20)),
                                 key="act_page_size")

        gb2 = GridOptionsBuilder.from_dataframe(df_act)
        gb2.configure_side_bar(); gb2.configure_selection("multiple",use_checkbox=True,pre_selected_rows=pre2)
        gb2.configure_pagination(paginationAutoPageSize=False,paginationPageSize=page_size)
        grid2 = AgGrid(df_act, gridOptions=gb2.build(), update_mode=GridUpdateMode.MODEL_CHANGED,
                       allow_unsafe_jscode=True, enable_enterprise_modules=True, key="act_ag")
        sel2 = _extract(grid2,"selected_rows"); edit2 = _extract(grid2,"data")
        st.session_state["act_sel_ids"] = [r["id"] for r in sel2 if r.get("id")]

        if st.button("💾 Save edits"):
            for row in edit2:
                payload = {k:row[k] for k in ("name","email","title","company") if k in row}
                requests.put(f"{API_URL}/prospects/{row['id']}", json=payload)
            st.success("Saved ✔"); st.cache_data.clear(); st.rerun()

        if len(sel2)==1:
            p = sel2[0]
            st.sidebar.markdown(f"### Timeline – {p['name']}")
            try:
                tl = requests.get(f"{API_URL}/prospects/{p['id']}/timeline").json()
                colors = {"scheduled":"#42a5f5","sent":"#66bb6a","failed":"#ef5350",
                          "in_progress":"#ffa726","completed":"#9e9e9e"}
                for s in tl:
                    st.sidebar.markdown(
                        f"**Step {s['step_number']}**: {s['template_name']}  \n"
                        f"Scheduled: {s['scheduled_at'] or '-'}  \n"
                        f"Sent: {s['sent_at'] or '-'}  \n"
                        f"<span style='background:{colors.get(s['status'],'#bbb')};color:white;"
                        f"padding:2px 4px;border-radius:4px;'>{_pretty_status(s['status'])}</span>  \n"
                        f"Opened: {s['opened_at'] or '-'}", unsafe_allow_html=True)
            except: st.sidebar.error("Timeline load failed.")

        if sel2:
            st.divider(); st.markdown(f"**Bulk actions ({len(sel2)})**")
            b1,b2,b3 = st.columns(3)
            with b1:
                pick2 = st.selectbox("Re-assign to sequence", list(name_to_id.keys()))
                if st.button("Re-assign"):
                    try:
                        r3 = requests.post(f"{API_URL}/assign-sequence", json={
                            "prospect_ids":[x['id'] for x in sel2],"sequence_id":name_to_id[pick2],"ventilate_days":0})
                        r3.raise_for_status(); st.success("Re-assigned ✔"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Failed: {e}")
            with b2:
                if st.button("Clear sequence"):
                    for x in sel2: requests.put(f"{API_URL}/prospects/{x['id']}", json={"sequence_id":None})
                    st.success("Cleared ✔"); st.cache_data.clear(); st.rerun()
            with b3:
                if st.button("❌ Delete"):
                    for x in sel2: requests.delete(f"{API_URL}/prospects/{x['id']}")
                    st.warning("Deleted ✔"); st.cache_data.clear(); st.rerun()

