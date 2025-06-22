# 📬 Email Platform

A modular email prospecting platform built with **Python**, **Streamlit**, and **SQLModel**. Schedule, manage, and send email campaigns using a sequence-based automation system.

---

## Features

- Add/edit/delete Prospects with titles, names, companies, emails
- Create and preview Email Templates (with BCC support)
- Design Sequences using templates and delay steps
- Visualize and manage Scheduled Emails
- CSV Import & Export of Prospects
- Streamlit-based interactive UI
- SQLite/SQLModel backend
- Email sending with SMTP
- Docker-ready architecture

---

## Project Structure

```bash
email-platform/
├── app/                    # Core backend logic
├── frontend/               # Streamlit frontend
├── scripts/                # Utilities: seed, scheduler
├── static/                 # Assets (e.g. logo)
├── templates/              # Optional email templates
├── tests/                  # Test scaffolding
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md

Quick Start

# Install dependencies (recommended in a virtualenv)
pip install -r requirements.txt

# Seed the database
python3 -m scripts.seed_db

# Run the app
./run_ui.sh

Run the Email Scheduler - To simulate email sends for scheduled campaigns:

python3 -m scripts.enqueue_emails


License
MIT License
