# Local Unified Stack

Use the local unified stack script when Docker image pulls are blocked by
external registry/CDN network issues.

## Command

```bash
cd /home/claudiu/projects/email-platform
./scripts/unified-local-stack.sh start
```

Other commands:

```bash
./scripts/unified-local-stack.sh status
./scripts/unified-local-stack.sh health
./scripts/unified-local-stack.sh stop
./scripts/unified-local-stack.sh restart
```

## Single Launch Entry Point

If you want one command that prefers Docker but automatically falls back to the
verified local stack, use:

```bash
./scripts/start-platform.sh
```

Modes:

```bash
./scripts/start-platform.sh auto
./scripts/start-platform.sh docker
./scripts/start-platform.sh local
```

Docker/network diagnostics:

```bash
./scripts/check-docker-prereqs.sh
```

## What It Starts

- worker: `/home/claudiu/projects/outreach-bot/app.py` on `127.0.0.1:5000`
- backend: `uvicorn app.main:app` on `127.0.0.1:8000`
- frontend: `next dev -p 3000` on `127.0.0.1:3000`

## Requirements

- `email-platform/.venv`
- `outreach-bot/.venv`
- `frontend/node_modules`

The script uses a local SQLite database for the backend:

- `DATABASE_URL=sqlite:///./email_platform.db`

and points the backend at the worker:

- `WORKER_BASE_URL=http://127.0.0.1:5000`

## Health Checks

The health command verifies:

- worker JSON campaign list
- backend worker-campaign proxy
- frontend login and authenticated `Acquire` route
