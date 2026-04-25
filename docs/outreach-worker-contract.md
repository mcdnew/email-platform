# Outreach Worker Contract

This document describes the current migration-stage API contract between:

- core platform: `/home/claudiu/projects/email-platform`
- acquisition worker: `/home/claudiu/projects/outreach-bot`

The contract is intentionally incremental. It lets the worker mirror important
events into the core platform without forcing a big-bang rewrite or immediate
replacement of the worker's local SQLite runtime.

## Required Core API Configuration In The Worker

Worker environment variables:

- `CORE_PLATFORM_URL`
  - internal API base URL, for example `http://backend:8000`
- `CORE_PLATFORM_PUBLIC_URL`
  - public platform base URL used in unsubscribe links
- `CORE_PLATFORM_API_KEY`
  - core platform API key for `X-API-Key`
- `UNSUBSCRIBE_SECRET`
  - shared unsubscribe secret so the worker can generate links accepted by the core `/unsubscribe` route

If these are not configured:

- the worker keeps running locally
- sync becomes best-effort no-op
- local outreach behavior is preserved

## Current Core Endpoints

### `POST /integrations/outreach/discoveries`

Purpose:

- mirror discovered leads into canonical `LeadCapture`
- create or update `Prospect` when an email is available
- create acquisition activity events

Expected payload:

```json
{
  "campaign_key": "acquire:lumber",
  "approval_required": true,
  "leads": [
    {
      "first_name": "Ada",
      "last_name": "Lovelace",
      "name": "Ada Lovelace",
      "email": "ada@example.com",
      "company": "Acme",
      "title": "Owner",
      "country": "US",
      "language": "en",
      "website": null,
      "linkedin": null,
      "notes": null,
      "fact": "Opened a new yard in 2026",
      "external_ref": "acquire:lumber:7"
    }
  ]
}
```

Notes:

- email is optional
- if email is missing, the core still records `LeadCapture`
- `approval_required=true` yields `pending_review`

### `POST /integrations/outreach/messages/sent`

Purpose:

- mirror an outbound acquisition send event
- upsert a Gmail `Conversation`
- move the prospect toward `awaiting_reply`
- update `last_contacted_at`
- record acquisition activity

Expected payload:

```json
{
  "email": "ada@example.com",
  "campaign_key": "acquire:lumber",
  "gmail_thread_id": "thread-777",
  "sequence_step": 1,
  "subject": "Quick question",
  "body": "Hello there",
  "sent_at": "2026-04-25T10:00:00+00:00"
}
```

Notes:

- worker should prefer canonical email over local prospect IDs
- core also accepts `prospect_id`, but email-based matching is the migration-friendly path

### `POST /integrations/outreach/replies`

Purpose:

- mirror inbound reply classification
- upsert Gmail conversation state
- record acquisition activity
- update lifecycle to `interested` when appropriate
- create suppression when intent is `UNSUBSCRIBE`

Expected payload:

```json
{
  "email": "ada@example.com",
  "campaign_key": "acquire:lumber",
  "intent": "INTERESTED",
  "body": "Tell me more",
  "gmail_thread_id": "thread-777",
  "from_email": "ada@example.com",
  "incoming_message_id": "msg-1",
  "received_at": "2026-04-25T10:05:00+00:00"
}
```

Recognized intents:

- `INTERESTED`
- `QUESTION`
- `NOT_NOW`
- `UNSUBSCRIBE`
- `OTHER`

### `POST /integrations/outreach/handoffs/nurture`

Purpose:

- turn an acquired/qualified prospect into a canonical nurture enrollment
- create or update `Enrollment`
- reuse the existing scheduler path
- record acquisition-to-nurture handoff activity

Expected payload:

```json
{
  "email": "ada@example.com",
  "campaign_key": "acquire:lumber",
  "sequence_id": 3,
  "qualified": true,
  "start_date": "2026-04-28",
  "ventilate_days": 0,
  "notes": "Warm handoff from outreach"
}
```

Notes:

- current worker code does not call this yet
- this endpoint exists so the handoff can be automated once the operator workflow is ready

## Current Worker Mirror Points

The worker currently mirrors:

- discovered leads
- outbound acquisition sends
- reply classifications
- manual unsubscribes

The worker currently does not yet mirror:

- every local status change
- campaign config updates
- historic SQLite data backfill
- acquisition analytics summaries

## Unsubscribe Link Strategy

Worker-generated outreach emails now prefer the core platform unsubscribe URL when:

- `CORE_PLATFORM_PUBLIC_URL` is configured
- `UNSUBSCRIBE_SECRET` or equivalent shared secret is configured

This lets the eventual one-domain deployment use the core platform's unsubscribe route instead of depending on the worker's public Flask route.

Fallback behavior:

- if the shared core unsubscribe settings are missing, the worker falls back to its current local unsubscribe URL

## Current Limitations

- worker still keeps local SQLite truth for many runtime concerns
- worker and core are not yet reconciled automatically
- deploy orchestration is not yet consolidated into one Docker stack
- outreach campaign YAML is still local to the worker

## Next Integration Steps

1. Decide whether worker-side approve/reject flows should call the core immediately or be replaced by the main web UI.
2. Add backfill/reconciliation tooling from worker SQLite into the core platform.
3. Shift more lifecycle ownership into the core and reduce worker-local authority.
4. Move unsubscribe and public link behavior fully onto the core domain.
5. Consolidate deploy orchestration once the remaining public worker-web dependencies are removed.
