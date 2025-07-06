# Email Platform

A modern, full-stack email campaign platform with:
- Sequence management and scheduling
- Prospect and template management
- Beautiful UI in Streamlit
- API built with FastAPI and SQLModel
- Supports SQLite and PostgreSQL databases

---

## Features

- Bulk prospect import and management
- Create and edit email templates (with Jinja placeholders)
- Build sequences (multi-step, with delays)
- Schedule and send emails, with analytics
- Test-send emails from templates
- Dark mode and responsive UI

---

## Requirements

- Python 3.10+
- Node.js (only if you want to build frontend assets for AgGrid, optional)
- PostgreSQL 13+ (recommended) or SQLite (for simple/local testing)
- [pipenv](https://pipenv.pypa.io/) or virtualenv for Python environment (recommended)

---

## Installation

1. **Clone the repository**
   ```sh
   git clone https://github.com/mcdnew/email-platform
   cd email-platform
   
2. Create and activate a virtual environment

python3 -m venv venv
source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt


4. Configure your .env file

Copy .env.example to .env (if provided) or create a new one:

DATABASE_URL=postgresql://<dbuser>:<dbpass>@localhost:5432/email_platform
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=yourpassword
MAX_EMAILS_PER_DAY=100


5. Initialize the database

 python -m scripts.init_db
 
 (Or for SQLite, it will create email_platform.db automatically)
 
Launching
1. Start the Backend API

uvicorn app.main:app --reload

2. Start the Streamlit Frontend

streamlit run frontend/main.py

The UI will run at http://localhost:8501.

User Manual
Login/Access
No login needed for local use (for deployment with auth, see advanced docs).

Main Workflow
Add Prospects

Use the “Add Prospect” form to add one manually.

Use “Import from CSV” for bulk import (see example CSV in examples/).

Create Email Templates

Go to “Templates” and create reusable email content.

Use placeholders like {{ name }} and preview rendering.

Build Sequences

Go to “Sequences”, create a sequence, and add steps with templates and delays.

Each step will be scheduled relative to the sequence start.

Assign Sequences to Prospects

Select prospects in the “Prospects” tab and assign a sequence (bulk or individually).

Monitor & Send

View scheduled and sent emails.

Use “Run Scheduler” (or wait for auto-scheduler) to send pending emails.

“Force Scheduler” is for dev/testing only.

Analytics

Dashboard view summarizes total sent, failed, opened, etc.

Dark Mode

Streamlit UI automatically uses system theme.

Testing

Use “Send Test” in the Templates tab to preview and test templates.

Tips
Only emails with status = "pending" will be sent.

Once sent, emails are marked and never sent again (prevents duplicates).

Always check your SMTP and database settings if sending fails.

Troubleshooting
Backend fails to start: Check .env and DB URL. Run python -m scripts.init_db.

Emails not sending: Verify SMTP settings in .env.

Dark mode text hard to read: Use the latest code (st.code() for previews).

Table/column errors: Re-initialize database after changing models.

Development
Make sure to activate your venv each time:
source venv/bin/activate

