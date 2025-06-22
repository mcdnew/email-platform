import streamlit as st
from sqlmodel import select
from app.database import get_session
from app.models import Prospect
# from app.utils import generate_tags  # if you later add tag-based filtering

def show():
    st.title("Prospects")

    # Form to add a new prospect
    st.subheader("Add New Prospect")
    with st.form("add_prospect"):
        title = st.selectbox("Title", ["", "Mr.", "Mrs.", "Ms.", "Dr."])
        name = st.text_input("Name")
        email = st.text_input("Email")
        company = st.text_input("Company")
        submitted = st.form_submit_button("Add")
        if submitted:
            if name and email:
                with next(get_session()) as session:
                    new = Prospect(title=title, name=name, email=email, company=company)
                    session.add(new)
                    session.commit()
                    st.success("Prospect added successfully!")
                    st.rerun()
            else:
                st.error("Name and Email are required.")

    st.divider()
    st.subheader("All Prospects")

    with next(get_session()) as session:
        all_prospects = session.exec(select(Prospect).order_by(Prospect.name)).all()

    for prospect in all_prospects:
        with st.expander(f"{prospect.name} ({prospect.email})"):
            col1, col2, col3 = st.columns([3, 3, 1])
            with col1:
                new_title = st.selectbox("Title", ["", "Mr.", "Mrs.", "Ms.", "Dr."], index=["", "Mr.", "Mrs.", "Ms.", "Dr."].index(prospect.title or ""), key=f"title_{prospect.id}")
                new_name = st.text_input("Name", prospect.name, key=f"name_{prospect.id}")
                new_email = st.text_input("Email", prospect.email, key=f"email_{prospect.id}")
            with col2:
                new_company = st.text_input("Company", prospect.company or "", key=f"company_{prospect.id}")

            with col3:
                if st.button("Save", key=f"save_{prospect.id}"):
                    with next(get_session()) as session:
                        p = session.get(Prospect, prospect.id)
                        p.title = new_title
                        p.name = new_name
                        p.email = new_email
                        p.company = new_company
                        session.add(p)
                        session.commit()
                        st.success("Prospect updated.")
                        st.rerun()

                if st.button("Delete", key=f"delete_{prospect.id}"):
                    with next(get_session()) as session:
                        p = session.get(Prospect, prospect.id)
                        session.delete(p)
                        session.commit()
                        st.warning("Prospect deleted.")
                        st.rerun()

