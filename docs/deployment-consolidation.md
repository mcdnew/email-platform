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

- `db`
- `backend`
- `frontend`
- `worker`

The `worker` service is built from:

- `/home/claudiu/projects/outreach-bot`

This is an intermediate consolidation step. It gives a single stack command
for local/server deployment as long as both repos are present side by side.

## Current Command

```bash
cd /home/claudiu/projects/email-platform
docker compose up --build
```

## Required Local/Server Layout

For the current compose file to work:

```text
~/projects/
  email-platform/
  outreach-bot/
```

The worker service currently mounts:

- `../outreach-bot/campaigns`
- `../outreach-bot/outreach.db`

This preserves current worker behavior while the migration is still in progress.

## Required Environment

Core repo:

- `.env` in `email-platform`

Worker repo:

- `.env` in `outreach-bot`

Important shared values:

- `API_KEY`
- `UNSUBSCRIBE_SECRET`
- `CORE_PLATFORM_PUBLIC_URL`

Worker-specific env remains in its own `.env` for now:

- Anthropic credentials
- Gmail OAuth client settings
- worker runtime settings

## Public Domain Strategy

Cloudflare should point at the unified platform domain.

Target behavior:

- public web app: frontend
- API: backend
- unsubscribe links from worker emails: core backend `/unsubscribe`

This is already partially supported:

- worker-generated unsubscribe links prefer the core platform URL when
  `CORE_PLATFORM_PUBLIC_URL` and the shared unsubscribe secret are configured

## Known Remaining Gaps

1. Worker source is still in a separate repo.
2. Worker local SQLite is still mounted and still holds runtime truth for some concerns.
3. Worker `.env` is still separate.
4. Worker Flask UI is not yet folded into the main frontend.
5. The outreach repo has no configured Git remote in the current local checkout.

## Next Deployment Steps

1. Reduce worker dependence on its public Flask UI.
2. Move more runtime truth from `outreach.db` into the core platform.
3. Decide whether to vendor the worker source into the core repo or keep a
   two-repo deployment layout temporarily.
4. Unify or better orchestrate env management across backend and worker.
5. Add reverse proxy production config for the Cloudflare-facing domain.
