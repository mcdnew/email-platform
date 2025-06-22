import streamlit as st
from sqlmodel import select
from app.database import get_session
from app.models import Sequence, SequenceStep, EmailTemplate

def show():
    st.title("Email Sequences")

    st.subheader("Create New Sequence")
    name = st.text_input("Sequence Name")
    if st.button("Add Sequence"):
        if name:
            with next(get_session()) as session:
                sequence = Sequence(name=name)
                session.add(sequence)
                session.commit()
                st.success("Sequence added.")
                st.rerun()
        else:
            st.error("Name is required")

    st.divider()
    st.subheader("Add Steps to Sequence")
    with next(get_session()) as session:
        sequences = session.exec(select(Sequence)).all()
        templates = session.exec(select(EmailTemplate)).all()

    if sequences and templates:
        selected_sequence = st.selectbox("Select Sequence", sequences, format_func=lambda s: s.name)
        selected_template = st.selectbox("Template", templates, format_func=lambda t: t.name)
        delay_days = st.number_input("Delay (in days)", min_value=1, value=1)
        if st.button("Add Step"):
            with next(get_session()) as session:
                step = SequenceStep(sequence_id=selected_sequence.id, template_id=selected_template.id, delay_days=delay_days)
                session.add(step)
                session.commit()
                st.success("Step added.")
                st.rerun()

    st.divider()
    st.subheader("All Sequences")

    with next(get_session()) as session:
        sequences = session.exec(select(Sequence)).all()

    for s in sequences:
        with st.expander(f"{s.name}"):
            new_name = st.text_input("Edit Name", s.name, key=f"name_{s.id}")
            cols = st.columns([1, 1])
            if cols[0].button("Save", key=f"save_{s.id}"):
                with next(get_session()) as session:
                    seq = session.get(Sequence, s.id)
                    seq.name = new_name
                    session.add(seq)
                    session.commit()
                    st.success("Updated.")
                    st.rerun()
            if cols[1].button("Delete", key=f"delete_{s.id}"):
                with next(get_session()) as session:
                    seq = session.get(Sequence, s.id)
                    session.delete(seq)
                    session.commit()
                    st.warning("Deleted.")
                    st.rerun()

