# TODOS

## Retry logic for failed emails
**What:** Add a `POST /retry-failed` endpoint (and optional cron) that retries `ScheduledEmail` rows with `status='failed'`, up to a configurable `max_retries` limit.
**Why:** Failed emails currently sit in the queue forever with no automatic recovery. Transient SMTP failures (timeouts, hiccups) require manual intervention to re-send.
**Pros:** Handles transient failures automatically. Improves deliverability without manual monitoring.
**Cons:** Requires adding `retry_count` field to `ScheduledEmail` model and a new Alembic migration. Must distinguish transient failures (retry) from permanent ones (bad address — don't retry).
**Context:** The `_process_emails()` refactor in Phase 1 makes this easy to bolt on — just call the same function with a filtered set of failed emails and a `max_retries` check. Start with a manual endpoint, add auto-retry later.
**Depends on:** Phase 1 hardening complete (especially `_process_emails()` refactor).

---

## Pagination for GET /sent-emails and GET /prospects
**What:** Add `?page=1&per_page=50` query params to `/sent-emails` and `/prospects` endpoints.
**Why:** Both endpoints currently load all rows into memory. At 10k+ sent emails this becomes slow (full table scan) and memory-heavy (~10MB+ per request).
**Pros:** Keeps API fast as volume grows. Simple to implement with SQLModel `offset`/`limit`.
**Cons:** Requires coordinated frontend changes (Streamlit now, Next.js later). The Streamlit AgGrid table currently expects all rows at once.
**Context:** Not urgent at current scale, but should be added before the Next.js frontend is built so the API contract is correct from day one.
**Depends on:** Nothing — can be done anytime, ideally before or during Phase 2 (Next.js).

---

## Separate UNSUBSCRIBE_SECRET from API_KEY
**What:** Add a dedicated `UNSUBSCRIBE_SECRET` env var for signing unsubscribe tokens, separate from `API_KEY`.
**Why:** `tracking.py` currently uses `settings.API_KEY` as the signing secret for `itsdangerous` unsubscribe tokens. This couples token security to API credentials — if the API key is rotated, all existing unsubscribe links in already-sent emails break.
**Pros:** API key rotation no longer invalidates existing unsubscribe links. Cleaner separation of concerns.
**Cons:** Requires a new env var and a migration path for existing tokens (or just accept a brief window of invalid links on first deploy).
**Context:** `app/tracking.py:10` — `URLSafeSerializer(settings.API_KEY, salt="unsubscribe")`. Two separate secrets would let you rotate each independently.
**Depends on:** Nothing.

---

## Structured JSON logging
**What:** Replace the current plain-text file logger with Python's `logging` module using a JSON formatter (or `structlog`).
**Why:** Current logs are unstructured plain text — hard to grep for specific errors, no log levels surfaced, no correlation IDs, impossible to ship to a log aggregator.
**Pros:** Easier to debug production issues. Immediately compatible with Loki, Datadog, CloudWatch, or any log aggregator. `structlog` adds context binding (e.g., `log.bind(prospect_id=X)`).
**Cons:** Minor refactor of logging calls throughout `app/`. ~30 min CC.
**Context:** Current error log path: `error_log.txt`. The `/error-log` endpoint reads it directly. Both the endpoint and the file path would need updating. The Docker Compose setup should also redirect stdout to a log driver.
**Depends on:** Nothing.
