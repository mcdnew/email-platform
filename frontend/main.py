# email-platform/frontend/main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from views import dashboard, prospects, templates, sequences, settings as st_settings, sent

PAGES = {
    "Dashboard": dashboard,
    "Prospects": prospects,
    "Templates": templates,
    "Sequences": sequences,
    "Sent Emails": sent,
    "Settings": st_settings
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to:", list(PAGES.keys()))
page = PAGES[selection]
page.show()

