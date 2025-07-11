# 📬 Email Platform

A modern, full-stack email campaign platform built with:

- ✅ FastAPI backend with SQLModel and Alembic migrations
- ✅ Streamlit frontend with a smooth UI and dashboard
- ✅ PostgreSQL (recommended) or SQLite for local dev
- ✅ SMTP email sending with scheduling, analytics, and sequences
- ✅ Docker + Bare-metal support

---

## 🚀 Features

- 📥 Bulk import and manage prospects
- 📝 Create email templates with Jinja-style placeholders (`{{ name }}`)
- 🔁 Build multi-step sequences with configurable delays
- 📆 Automatic email scheduling with CRON-based delivery
- 📊 Analytics dashboard with open/click tracking
- 🧪 Send test emails before launch
- 🌙 Auto dark mode with responsive frontend
- 🐳 Docker or bare-metal deployment

---

## ⚙️ Requirements

### For **Bare Metal** deployment:

- Python 3.10+
- PostgreSQL 13+ running locally
- Node.js *(optional — for AgGrid custom builds)*
- Virtualenv or Pipenv

### For **Docker Deployment**:

- Docker Engine + Docker Compose
- Linux/macOS/Windows with WSL2 support

---

## 🔧 Installation (Manual/Bare-Metal)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/email-platform
cd email-platform
```

### 2. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure .env file

```env
# .env
DATABASE_URL=postgresql://email_user:strongpassword@localhost:5432/email_platform
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
MAX_EMAILS_PER_DAY=100
```

### 5. Set up the database

Make sure PostgreSQL is running and you have created the user/database:

```bash
# As postgres superuser
sudo -u postgres psql

CREATE ROLE email_user WITH LOGIN PASSWORD 'strongpassword';
CREATE DATABASE email_platform OWNER email_user;
\q
```

Then apply migrations:

```bash
alembic upgrade head
```

---

## 🖥 Launching (Manual Dev)

### 1. Start the FastAPI backend

```bash
uvicorn app.main:app --reload
```

### 2. Start the Streamlit frontend

```bash
cd frontend
streamlit run main.py
```

**Visit:** http://localhost:8501

---

## 🐳 Docker Deployment

### 1. Build & run

```bash
docker compose up --build
```

### 2. Check services

- **Frontend:** http://localhost:8501
- **Backend API:** http://localhost:8000/docs

---

## 🔐 Environment Files

- **`.env`**: root config for backend and database
- **`frontend/.env`**: contains API_URL and APP_PASSWORD for frontend Streamlit

---

## 📋 Usage Guide

### Add Prospects

- Add manually or import CSV
- **CSV format:** `name,email,company,title`

### Templates

- Create reusable email templates
- Supports `{{ name }}`, `{{ company }}`, etc.

### Sequences

- Build step-based sequences
- Assign delays (e.g. Step 1: Day 0, Step 2: Day 3)

### Assign Sequences

- In the "Prospects" tab, assign a sequence
- Emails will be scheduled automatically

### Send Emails

- Emails are sent by CRON via `run_scheduler.sh`
- You can also click "Run Scheduler" manually

### Analytics

Dashboard shows:
- Total sent
- Failures
- Open rate
- Recent activity

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| SMTP fails | Check your .env and credentials |
| Database errors | Recreate the DB or use `alembic downgrade base` then `upgrade head` |
| Email not sending | Check if status = pending and run scheduler |
| Cannot delete sequence/template | Make sure it's not referenced in ScheduledEmail |
| Port already in use | Stop other services on 8000/8501 or edit the ports in docker-compose.yml |

---

## 🛠 Development

### Init/reset database (dangerous in production):

```bash
curl -X POST http://localhost:8000/reset-all
```

### Alembic Commands

```bash
alembic revision --autogenerate -m "new changes"
alembic upgrade head
```

---

## ☁️ Cloud Deployment (e.g. AWS Lightsail)

1. Provision an Ubuntu instance
2. SSH in, install Docker and Git
3. Clone repo, set up .env files
4. Run:

```bash
docker compose up --build -d
```

See `docs/deployment_manual.md` for full steps.

---

## 🧪 Testing Templates

Use the "Send Test" tab to preview a template:

- Fill in subject, body, recipient
- Variables like `{{ name }}` will be filled

---

## 🧼 Clean Development Environment

### To reset everything:

**Docker:**
```bash
docker compose down -v
rm -rf db_data/ email_platform.db logs/
```

**Bare-metal:**
```bash
alembic downgrade base
alembic upgrade head
```

---

## 📁 Project Structure

```
email-platform/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── mailer.py
│   └── ...
├── frontend/
│   └── main.py
├── migrations/
│   └── versions/
├── .env
├── docker-compose.yml
└── README.md
```

---

## 📄 License

Proprietary © [Claudiu Muntianu]
