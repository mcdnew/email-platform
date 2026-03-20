# TODOS

## ~~Retry logic for failed emails~~
**Completed:** v1.0 (2026-03-20) — commit `a57c9ed`
`POST /retry-failed` endpoint added. Resets failed emails to pending (up to `MAX_RETRIES`), skips unsubscribed/deleted prospects, re-runs `_process_emails`. `retry_count` field added to `ScheduledEmail` with Alembic migration. 10 regression tests in `tests/test_retry_and_unsubscribe_secret.py`.

---

## ~~Pagination for GET /sent-emails and GET /prospects~~
**Completed:** Phase 2 (2026-03-20)
Added `?page=&per_page=&sort_by=&order=&search=` to `/prospects` and `?page=&per_page=&sort_by=&order=&status_filter=` to `/sent-emails`. Both return `{ items, total, page, per_page, pages }`. TanStack Table in the Next.js frontend uses server-side sort/filter throughout.

---

## ~~Separate UNSUBSCRIBE_SECRET from API_KEY~~
**Completed:** v1.0 (2026-03-20) — commit `5d079cc`
`UNSUBSCRIBE_SECRET` env var added to `app/config.py` and `app/tracking.py`. Falls back to `API_KEY` then `dev-secret` for backward compat. Rotating `API_KEY` no longer invalidates existing unsubscribe links. Regression tests in `tests/test_retry_and_unsubscribe_secret.py`.

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

## ~~Structured JSON logging~~
**Completed:** v1.0 (2026-03-20)
`app/logging_config.py` — `JsonFormatter` + `configure_logging()`. All `app.*` loggers emit JSON lines to stdout and `error_log.txt`. Structured events: `email_sent`, `email_failed`, `email_skipped_unsubscribed`, `email_skipped_missing`, `smtp_failure`, `template_render_error`, `email_opened`, `daily_limit_reached`, `unhandled_exception`. `/error-log` endpoint returns parsed `{"entries": [...]}`. `LOG_LEVEL` and `LOG_PATH` configurable via env.
