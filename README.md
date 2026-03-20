# 📬 Email Platform

A modern, full-stack email campaign platform built with:

- ✅ FastAPI backend with SQLModel and Alembic migrations
- ✅ Next.js 14 frontend with TypeScript, Tailwind CSS, TanStack Table, and Tiptap rich-text editor
- ✅ PostgreSQL (recommended) or SQLite for local dev
- ✅ SMTP email sending with scheduling, analytics, and sequences
- ✅ API key authentication (`X-API-Key` header) on all endpoints
- ✅ Open-tracking pixel with unsubscribe token support
- ✅ 42-test suite with pytest (71% coverage)
- ✅ Docker + Bare-metal support

---

## 🚀 Features

- 📥 Bulk import and manage prospects
- 📝 Create email templates with Jinja-style placeholders (`{{ name }}`)
- 🔁 Build multi-step sequences with configurable delays
- 📆 Automatic email scheduling with CRON-based delivery
- 📊 Analytics dashboard with open tracking (pixel-based)
- 🔐 API key auth — all endpoints require `X-API-Key` (disabled when unset for local dev)
- 🚫 Unsubscribe links via signed tokens (itsdangerous) — purges pending emails on click
- 🧪 Send test emails before launch
- 📱 Mobile-responsive frontend with sidebar nav and hamburger drawer
- 🐳 Docker or bare-metal deployment

---

## ⚙️ Requirements

### For **Bare Metal** deployment:

- Python 3.10+
- PostgreSQL 13+ running locally
- Node.js 18+ *(required for the Next.js frontend)*
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
DATABASE_URL=postgresql://email_user:<password>@localhost:5432/email_platform
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
MAX_EMAILS_PER_DAY=100
TIMEZONE=Europe/Paris

# API key — required for all endpoints. Leave empty to disable auth in local dev.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
API_KEY=
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

### 2. Start the Next.js frontend

```bash
cd frontend
npm install
npm run dev
```

**Visit:** http://localhost:3000

---

## 🐳 Docker Deployment

### 1. Build & run

```bash
docker compose up --build
```

### 2. Check services

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs

---

## 🔐 Environment Files

- **`.env`**: root config for backend and database (see `.env.example` for all variables)
- **`frontend/.env.local`**: contains `API_URL` for the Next.js frontend (points to FastAPI backend)

Key variables added in Phase 1 hardening:

| Variable | Purpose |
|----------|---------|
| `API_KEY` | Shared secret for `X-API-Key` header auth. Leave empty to disable (dev only). |
| `TIMEZONE` | Timezone for send-window enforcement (e.g. `Europe/Paris`). |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Required when using Docker Compose. |

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
| SMTP fails | Check your `.env` credentials and SMTP server/port |
| Database errors | Recreate the DB or use `alembic downgrade base` then `upgrade head` |
| Email not sending | Check status = `pending` and `send_at` is in the past, then run force-scheduler |
| Cannot delete sequence/template | Remove it from all sequence steps first |
| Port already in use | Stop other services on 8000/3000 or change ports in `docker-compose.yml` |
| 401 Unauthorized | Set `API_KEY` in `.env` (or leave empty to disable auth in dev) |
| Unsubscribe link broken | Ensure `API_KEY` hasn't changed since the link was generated — tokens are signed with it |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
# with coverage:
pytest tests/ --cov=app --cov-report=term-missing
```

The test suite uses an in-memory SQLite database and mocks SMTP — no external services needed.

---

## 🛠 Development

### Init/reset database (dangerous in production):

```bash
# Requires DEV_MODE=true in .env
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

See `email_platform_deployment_manual.md` for full steps.

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
│   ├── main.py          # FastAPI app, all routes, scheduler logic
│   ├── models.py        # SQLModel table definitions
│   ├── mailer.py        # SMTP send + tracking pixel injection
│   ├── tracking.py      # Unsubscribe token sign/verify (itsdangerous)
│   ├── crud.py          # DB helpers and bulk sequence assignment
│   ├── config.py        # Settings loaded from .env
│   ├── database.py      # SQLAlchemy engine + session
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── dev.py           # Dev-only endpoints (generate test data)
│   └── routes/
│       └── open_tracking.py  # GET /track_open — pixel endpoint
├── frontend/
│   ├── src/app/         # Next.js 14 App Router pages
│   │   ├── (app)/       # Authenticated layout (dashboard, prospects, templates, sequences, queue, sent, settings)
│   │   ├── api/         # Next.js API routes (auth cookie + proxy to FastAPI)
│   │   └── login/       # Login page
│   ├── src/components/  # AppShell, TiptapEditor, PaginationBar, StatusBadge, Toast, TimelineDrawer
│   ├── src/lib/         # API client (api.ts), type definitions (types.ts)
│   └── package.json     # Next.js 14, TanStack Table, Recharts, React Query
├── migrations/
│   └── versions/        # Alembic migration files
├── tests/               # pytest suite (42 tests, 71% coverage)
├── .env.example         # Template for all environment variables
├── docker-compose.yml
├── run_scheduler.sh     # Cron wrapper — calls POST /run-scheduler
├── TODOS.md             # Deferred work items
└── README.md
```

---

## 📄 License

Proprietary © [Claudiu Muntianu]
