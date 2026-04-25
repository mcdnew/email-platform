# Platform Migration Foundation

This repository is the canonical target for the unified platform.

Current source repos:

- Core platform target: `/home/claudiu/projects/email-platform`
- Acquisition worker source: `/home/claudiu/projects/outreach-bot`
- Mobile capture app source: `/home/claudiu/projects/business-card-processor/CardScanner`

## End State

The target platform is:

- one main web app
- one main API/backend
- one canonical PostgreSQL database
- one deployable Docker-based server stack
- one Cloudflare-fronted public domain

Operationally, the deployed stack may still contain multiple internal services:

- web
- API
- worker
- database
- persistent asset storage

That still counts as one application boundary and one coordinated deployment.

## Phase 0 / 1 Scope

This first implementation tranche establishes the migration foundation inside the core repo without breaking existing behavior.

Delivered in this phase:

- shared lifecycle vocabulary
- foundational canonical tables
- explicit migration ownership rules in `AGENTS.md`
- in-repo architecture artifact

New foundational concepts added in this phase:

- `Enrollment`
- `Suppression`
- `ActivityEvent`
- `Conversation`
- `Asset`
- `LeadCapture`

Bridge fields added to the current `Prospect` model:

- `lifecycle_stage`
- `source_type`
- `source_ref`
- `owner`
- `last_contacted_at`
- `interested_at`
- `qualified_at`

These bridge fields keep the current application functional while introducing the vocabulary needed for the broader platform migration.

## Ownership Rules

Long-term source of truth:

- contacts, suppressions, enrollments, activity, assets, and canonical messaging state live in this repo

Temporary migration boundaries:

- `outreach-bot` remains the acquisition worker runtime
- `CardScanner` remains a mobile client with offline cache

Not allowed long term:

- outreach SQLite owning contact lifecycle or suppressions
- CardScanner local storage acting as the canonical CRM
- Nextcloud acting as live runtime storage

## CardScanner And Nextcloud

CardScanner local DB/storage should be treated as:

- offline cache
- local draft store
- retry queue
- local file staging area

It must not remain the final system of record after sync.

Nextcloud should be treated as:

- backup/archive target for DB dumps and asset snapshots

It must not become:

- canonical DB
- canonical object storage
- required runtime dependency

## Next Implementation Steps

1. Adapt the current CardScanner-facing endpoints to write through the new canonical concepts.
2. Define the acquisition worker contract for discovery, replies, suppressions, and handoff.
3. Move critical business truth out of outreach SQLite and into the core platform.
4. Build the acquisition-to-nurture handoff in the core service layer.
5. Consolidate operator UI into the main web app.
