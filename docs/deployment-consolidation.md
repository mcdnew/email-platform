# Deployment Consolidation

This document captures the current migration-stage deployment path toward the
end-state goal of:

- one product
- one server
- one coordinated Docker deployment
- one public Cloudflare-fronted domain

## Current Consolidated Stack

The main deployment entrypoint is now the core repo:

- `/home/claudiu/projects/email-platform/docker-compose.yml`

It currently runs:

- `proxy`
- `db`
- `backend`
- `frontend`
- `worker`
- optional `worker-runner`

The `worker` service is built from:

- `/home/claudiu/projects/outreach-bot`

This is an intermediate consolidation step. It gives a single stack command
for local/server deployment as long as both repos are present side by side.

## Current Command

```bash
cd /home/claudiu/projects/email-platform
cp .env.example .env
cp worker.env.example worker.env
docker compose up --build
```

If the reverse-proxy image cannot be pulled in the current environment, the
stack can still run without it because `proxy` is now placed behind the
optional Compose profile `proxy`.

Default local/runtime validation path:

```bash
docker compose up --build
```

Production-style path with reverse proxy:

```bash
docker compose --profile proxy up --build
```

If you want the background acquisition loop active too:

```bash
docker compose --profile runner up --build
```

If you want both proxy and runner:

```bash
docker compose --profile proxy --profile runner up --build
```

## Required Local/Server Layout

For the current compose file to work:

```text
~/projects/
  email-platform/
  outreach-bot/
```

The worker source is still built from `../outreach-bot`, but its runtime data is
now centralized into this repo:

- `./worker-data/campaigns`
- `./worker-data/outreach.db`

This preserves current worker behavior while the migration is still in progress.

Important runtime split:

- `worker`: Flask JSON/API surface on port 5000 for the core app to query/control
- `worker-runner`: optional long-running acquisition loop (`python main.py run`)

This split is necessary because the core app depends on worker JSON endpoints,
while the runner loop is an execution concern rather than an operator/API concern.

## Required Environment

Core repo:

- `.env` in `email-platform`
- `worker.env` in `email-platform`

Important shared values:

- `API_KEY`
- `UNSUBSCRIBE_SECRET`
- `CORE_PLATFORM_PUBLIC_URL`
- `PUBLIC_HOST`

Worker-specific env is now expected in `worker.env` in the core repo:

- Anthropic credentials
- Gmail OAuth client settings
- worker runtime settings

## Public Domain Strategy

Cloudflare should point at the unified platform domain.

Target behavior:

- public web app: frontend through `proxy`
- API paths for mobile or backend-facing external use: `/api/core/*`
- unsubscribe links from worker emails: core backend `/unsubscribe`
- tracking links: core backend `/track_open` and `/track_click`

Fallback local behavior without the proxy profile:

- frontend is exposed on `:3000`
- backend is exposed on `:8000`

This is already partially supported:

- worker-generated unsubscribe links prefer the core platform URL when
  `CORE_PLATFORM_PUBLIC_URL` and the shared unsubscribe secret are configured

## Known Remaining Gaps

1. Worker source is still in a separate repo.
2. Worker local SQLite is still mounted and still holds runtime truth for some concerns.
3. Worker Flask UI is not yet folded into the main frontend.
4. Reverse-proxy config is present, but not yet validated in a live end-to-end Cloudflare deployment.

## Next Deployment Steps

1. Reduce worker dependence on its public Flask UI.
2. Move more runtime truth from `outreach.db` into the core platform.
3. Decide whether to vendor the worker source into the core repo or keep a
   two-repo deployment layout temporarily.
4. Unify or better orchestrate env management across backend and worker.
5. Add reverse proxy production config for the Cloudflare-facing domain.
