# email-platform/frontend/main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from views import dashboard, prospects, templates, sequences, settings as st_settings

st.set_page_config(page_title="Email Platform Dashboard", layout="wide")

PAGES = {
    "Dashboard": dashboard,
    "Prospects": prospects,
    "Templates": templates,
    "Sequences": sequences,
    "Settings": st_settings
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to:", list(PAGES.keys()))
page = PAGES[selection]
page.show()

