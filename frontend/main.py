# email-platform/frontend/main.py

import os
from dotenv import load_dotenv
import streamlit as st
import sys

# ──────────────────────────────────────────────────────────────────────────────
# 1) Load environment (so APP_PASSWORD is picked up if you have a .env file)
load_dotenv()

# 2) Simple password protection
#PASSWORD = os.getenv("APP_PASSWORD", "changeme")
PASSWORD = "agent007"

if "authed" not in st.session_state:
    st.session_state.authed = False

def do_login():
    st.markdown("### 🔐 Enter your password to continue")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("❌ Wrong password")

if not st.session_state.authed:
    do_login()
    st.stop()
# ──────────────────────────────────────────────────────────────────────────────

# Now that we’re authenticated, set up the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from views import (
    dashboard,
    prospects,
    templates,
    sequences,
    settings as st_settings,
    sent,
    dev,
)

PAGES = {
    "Dashboard": dashboard,
    "Prospects": prospects,
    "Templates": templates,
    "Sequences": sequences,
    "Sent Emails": sent,
    "Settings": st_settings,
}

# Only show Dev Tools if DEV_MODE=true
if os.getenv("DEV_MODE", "false").lower() == "true":
    PAGES["Dev Tools"] = dev

st.set_page_config(page_title="Email Platform", layout="wide")

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to:", list(PAGES.keys()))
page = PAGES[selection]
page.show()

