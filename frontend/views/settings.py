import streamlit as st
from app.config import settings

def show():
    st.title("Settings")

    st.subheader("SMTP Configuration")
    st.text_input("SMTP Server", value=settings.SMTP_SERVER, disabled=True)
    st.number_input("SMTP Port", value=settings.SMTP_PORT, disabled=True)
    st.text_input("SMTP Username", value=settings.SMTP_USER, disabled=True)
    st.text_input("SMTP Password", value="********", type="password", disabled=True)

    st.info("To update SMTP settings, edit your `.env` file and restart the application.")

    st.subheader("Database")
    st.code(settings.DB_URL, language="text")

    st.info("This app uses SQLModel and SQLAlchemy to manage the database.")

