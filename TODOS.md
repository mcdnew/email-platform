# TODOS

## Retry logic for failed emails
**What:** Add a `POST /retry-failed` endpoint (and optional cron) that retries `ScheduledEmail` rows with `status='failed'`, up to a configurable `max_retries` limit.
**Why:** Failed emails currently sit in the queue forever with no automatic recovery. Transient SMTP failures (timeouts, hiccups) require manual intervention to re-send.
**Pros:** Handles transient failures automatically. Improves deliverability without manual monitoring.
**Cons:** Requires adding `retry_count` field to `ScheduledEmail` model and a new Alembic migration. Must distinguish transient failures (retry) from permanent ones (bad address — don't retry).
**Context:** The `_process_emails()` refactor in Phase 1 makes this easy to bolt on — just call the same function with a filtered set of failed emails and a `max_retries` check. Start with a manual endpoint, add auto-retry later.
**Depends on:** Phase 1 hardening complete (especially `_process_emails()` refactor).

---

## ~~Pagination for GET /sent-emails and GET /prospects~~
**Completed:** Phase 2 (2026-03-20)
Added `?page=&per_page=&sort_by=&order=&search=` to `/prospects` and `?page=&per_page=&sort_by=&order=&status_filter=` to `/sent-emails`. Both return `{ items, total, page, per_page, pages }`. TanStack Table in the Next.js frontend uses server-side sort/filter throughout.

---

## Separate UNSUBSCRIBE_SECRET from API_KEY
**What:** Add a dedicated `UNSUBSCRIBE_SECRET` env var for signing unsubscribe tokens, separate from `API_KEY`.
**Why:** `tracking.py` currently uses `settings.API_KEY` as the signing secret for `itsdangerous` unsubscribe tokens. This couples token security to API credentials — if the API key is rotated, all existing unsubscribe links in already-sent emails break.
**Pros:** API key rotation no longer invalidates existing unsubscribe links. Cleaner separation of concerns.
**Cons:** Requires a new env var and a migration path for existing tokens (or just accept a brief window of invalid links on first deploy).
**Context:** `app/tracking.py:10` — `URLSafeSerializer(settings.API_KEY, salt="unsubscribe")`. Two separate secrets would let you rotate each independently.
**Depends on:** Nothing.

---

## HTML email templates (Tiptap)
**What:** Replace the plain `<textarea>` template editor with Tiptap (ProseMirror) to support HTML emails — bold, italic, links, images.
**Why:** Phase 2 chose a plain textarea + live preview because current emails are plain-text. If HTML emails are ever needed, Tiptap is the right WYSIWYG editor for Next.js.
**Pros:** Rich formatting. Supports branded emails with inline styles.
**Cons:** ~150KB bundle addition. Requires a custom Tiptap extension for `{{name}}`-style variable insertion. HTML→plain-text round-trip for SMTP multipart emails.
**Context:** Phase 2 deferred this in eng review (2026-03-20). Templates currently use `{{variable}}` Jinja-style syntax in plain text. Server-side rendering via Jinja2 is already wired.
**Depends on:** Phase 2 complete.

---

## Playwright e2e smoke tests
**What:** Add Playwright tests covering the critical happy path: login → create prospect → assign sequence → verify scheduled email appears in queue.
**Why:** Vitest + Testing Library covers all unit/integration paths. Playwright covers the full stack integration that unit tests can't — real browser, real Next.js, real FastAPI.
**Pros:** Catches integration regressions that unit tests miss. Runs in CI as a deployment gate.
**Cons:** Requires a running stack in CI (Docker Compose or docker-compose up in the CI job). Tests are slower (5-30s) and brittle to UI changes.
**Context:** Deferred during Phase 2 eng review (2026-03-20) in favor of Vitest for speed. Add as a Phase 3 supplement once the frontend is stable.
**Depends on:** Phase 2 complete (Next.js frontend stable).

---

## Structured JSON logging
**What:** Replace the current plain-text file logger with Python's `logging` module using a JSON formatter (or `structlog`).
**Why:** Current logs are unstructured plain text — hard to grep for specific errors, no log levels surfaced, no correlation IDs, impossible to ship to a log aggregator.
**Pros:** Easier to debug production issues. Immediately compatible with Loki, Datadog, CloudWatch, or any log aggregator. `structlog` adds context binding (e.g., `log.bind(prospect_id=X)`).
**Cons:** Minor refactor of logging calls throughout `app/`. ~30 min CC.
**Context:** Current error log path: `error_log.txt`. The `/error-log` endpoint reads it directly. Both the endpoint and the file path would need updating. The Docker Compose setup should also redirect stdout to a log driver.
**Depends on:** Nothing.
