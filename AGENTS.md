# AGENTS.md

## Role & Intent

This repository is the **target core platform** for migrating and integrating three existing apps into one deployable product:

- Core platform target: `/home/claudiu/projects/email-platform`
- Acquisition worker source: `/home/claudiu/projects/outreach-bot`
- Mobile capture app source: `/home/claudiu/projects/business-card-processor/CardScanner`

The end goal is:

- one product
- one main web app
- one main API/backend
- one canonical database
- one source of truth for contacts and messaging state
- one server deployment
- one Docker-based production stack
- one Cloudflare-pointed public domain

The mobile scanner may remain a separate repo and separate build artifact. That is acceptable. It must become a **client of the unified platform**, not a separate business system.

This file is the operating contract for Codex work in this repo. Follow it strictly.

## Operating Principles

- Treat `/home/claudiu/projects/email-platform` as the permanent center of gravity.
- Build the domain model first, then integration adapters, then UI consolidation, then deployment consolidation.
- Preserve existing behavior while shifting state ownership underneath.
- Prefer incremental migration with tests over rewrites.
- Do not merge repos early just because they are related.
- Do not allow more than one long-term source of truth for the same business concept.
- Design for one deployed platform stack, not one process.
- Use the lightest path that preserves correctness.

## Migration Outcome

The intended product shape is:

- `web`: operator UI in this repo
- `api`: canonical backend in this repo
- `worker`: acquisition/discovery/reply runtime evolved from `outreach-bot`
- `mobile`: business-card capture client from `CardScanner`

The intended platform modules are:

- `Capture`
  - business card OCR
  - contact capture
  - tags, notes, voice notes, card photos
- `Acquire`
  - prospect discovery
  - cold outreach
  - Gmail thread handling
  - reply classification
  - qualification
- `Nurture`
  - templates
  - sequences
  - scheduled sends
  - lifecycle messaging
- `Ops`
  - contacts
  - companies
  - suppressions
  - activity timeline
  - analytics
  - settings

## Source Repos

Codex may need to inspect and migrate from these directories:

- `/home/claudiu/projects/email-platform`
- `/home/claudiu/projects/outreach-bot`
- `/home/claudiu/projects/business-card-processor/CardScanner`

When implementing migration:

- make all canonical contracts and deployment orchestration live here in `/home/claudiu/projects/email-platform`
- keep CardScanner as a separate mobile client repo unless explicitly told otherwise
- keep `outreach-bot` separate until worker-contract migration and state migration are complete

## Canonical Ownership Rules

Long-term canonical owners:

- contacts: this repo
- companies: this repo
- campaigns: this repo
- sequences and sequence steps: this repo
- templates: this repo
- enrollments: this repo
- suppressions/unsubscribes/do-not-contact: this repo
- activity timeline: this repo
- assets metadata: this repo
- lead capture records: this repo
- message/conversation history: this repo

Temporary runtime owners during migration:

- Gmail polling/runtime state: `outreach-bot`
- mobile offline cache and pending uploads: `CardScanner`

State that must not remain authoritative outside this repo:

- contact lifecycle status
- unsubscribe/suppression state
- enrollment state
- handoff state between acquisition and nurture
- asset metadata
- canonical contact history

## Canonical Entities

Codex must converge the platform toward these first-class concepts:

- `Contact`
- `Company`
- `Campaign`
- `Sequence`
- `SequenceStep`
- `Template`
- `Enrollment`
- `Message`
- `Conversation`
- `ReplyClassification`
- `Suppression`
- `ActivityEvent`
- `Asset`
- `LeadCapture`

Do not endlessly overload existing `Prospect` tables if missing concepts need to become explicit. Adapt existing tables where appropriate, but converge toward these concepts.

## Canonical Lifecycle

Contact lifecycle:

- `captured`
- `pending_review`
- `ready_for_outreach`
- `outreach_active`
- `awaiting_reply`
- `interested`
- `qualified`
- `nurture_active`
- `opportunity`
- `customer`
- `lost`
- `archived`

Orthogonal blocking/status flags:

- `unsubscribed`
- `bounced`
- `do_not_contact`
- `invalid_email`
- `duplicate`
- `blocked`

Enrollment lifecycle:

- `draft`
- `active`
- `paused`
- `completed`
- `cancelled`
- `failed`

Conversation lifecycle:

- `open`
- `waiting_on_us`
- `waiting_on_contact`
- `closed`
- `suppressed`

Rules:

- Keep contact lifecycle separate from enrollment lifecycle.
- Keep suppression separate from lifecycle.
- Keep provider-specific thread state separate from contact lifecycle.
- Do not invent new status vocabularies in migration code without strong justification.

## CardScanner Policy

Working directory:

- `/home/claudiu/projects/business-card-processor/CardScanner`

Treat CardScanner as:

- a first-party mobile capture client
- an offline-capable sync client
- a local cache and staging area for captured data

Do not treat CardScanner as:

- a canonical CRM
- the system of record
- the final owner of contact state
- the final owner of asset state

CardScanner local database/storage policy:

- local DB/storage is allowed for offline UX
- local DB/storage may hold:
  - draft contact edits
  - OCR results
  - sync status
  - retry metadata
  - local file URIs
- local DB/storage must not remain the long-term source of truth after sync

After successful sync:

- server-side canonical `Contact` becomes authoritative
- server-side canonical `Asset` metadata becomes authoritative
- mobile local data becomes cache + offline view + retry support only

CardScanner schema rule:

- do not try to impose the mobile-local schema onto the platform schema
- instead, map mobile records into canonical server entities

## Nextcloud Policy

Current Nextcloud usage must be treated as backup/archive integration only.

Allowed roles for Nextcloud:

- scheduled backup destination for PostgreSQL dumps
- scheduled backup/archive destination for uploaded assets
- export destination for snapshots or operator exports

Disallowed roles for Nextcloud:

- primary transactional database
- primary object storage contract
- live canonical contact store
- required dependency for core runtime
- required dependency for mobile sync

Operational rule:

- canonical DB lives in PostgreSQL
- canonical asset metadata lives in this platform DB
- canonical files live in platform-managed persistent storage
- Nextcloud may receive copies via backup jobs

## Outreach Worker Policy

Working directory:

- `/home/claudiu/projects/outreach-bot`

Treat `outreach-bot` as:

- the source code for the acquisition worker
- a Gmail/discovery/reply automation engine
- a background runtime that will be integrated into the platform

Do not treat `outreach-bot` as:

- the permanent operator UI
- the permanent owner of contact lifecycle
- the permanent owner of suppression state
- the permanent owner of message history

Migration rule:

- its SQLite database may temporarily remain a worker cache/runtime store
- it must stop being authoritative for business truth

Priority for state migration out of outreach SQLite:

1. suppressions
2. lifecycle states
3. message and reply records
4. conversation/thread linkage
5. analytics-critical history

## End-State Deployment

Final deployment target is one platform stack on one server, fronted by Cloudflare.

Acceptable end-state deployment shape:

- reverse proxy
- frontend service
- API service
- worker service
- PostgreSQL
- persistent asset volume
- optional backup job

This still counts as:

- one app
- one deploy
- one server

because it is one platform boundary and one coordinated deployment stack.

Recommended production shape:

- one Docker Compose-based deployment from this repo
- one domain or one main domain with subpaths
- one reverse proxy entrypoint
- one shared canonical database
- one shared persistent storage strategy

Do not try to achieve “one deploy” by forcing everything into one process.

## Explicit Do / Do Not

Do:

- start all migration work from this repo unless a subtask explicitly belongs in a source repo
- create architecture and migration artifacts in this repo
- add missing first-class domain models here
- preserve backward compatibility where needed during migration
- formalize API contracts before swapping clients/workers over
- unify suppression logic early
- lock lifecycle transitions with tests
- move business truth inward before consolidating UI
- centralize deploy/orchestration here

Do not:

- do not merge the three repos into one codebase early
- do not keep separate unsubscribe systems
- do not keep separate canonical contact stores
- do not let mobile remain a second CRM
- do not let outreach SQLite remain authoritative long term
- do not make UI-first decisions before state ownership is fixed
- do not remove working flows before verified replacements exist
- do not rely on Nextcloud for runtime-critical behavior

## Order Of Operations

Codex must follow this order unless a deviation is explicitly documented.

### Phase 0: Lock Architecture

Do:

- create migration docs in this repo
- record working directories
- record ownership rules
- record canonical entities
- record lifecycle rules
- record deployment target

Do not:

- start large code moves before architecture is locked

### Phase 1: Expand Core Domain Model

Do:

- add first-class models/services for:
  - `Enrollment`
  - `Suppression`
  - `ActivityEvent`
  - `Conversation`
  - `Asset`
  - `LeadCapture`
- preserve backward compatibility with current flows

Do not:

- stretch current `Prospect` structures forever instead of modeling missing concepts

### Phase 2: Normalize Statuses

Do:

- add canonical enums/constants
- map current email-platform statuses
- map current outreach statuses
- map capture/import states
- add transition validation and tests

Do not:

- leave permanent status translation chaos across modules

### Phase 3: Stabilize CardScanner Contract

Do:

- keep CardScanner as separate repo/client
- document stable API contract in this repo
- map uploads to canonical `Asset` records
- map sync records to canonical `Contact` and `LeadCapture`
- keep local mobile DB as cache/offline store only

Do not:

- redesign the platform around the mobile-local schema

### Phase 4: Build Acquisition Worker Contract

Do:

- define worker-facing APIs/events for:
  - discovered leads
  - review queue entries
  - approvals/rejections
  - outbound messages
  - inbound replies
  - classifications
  - suppressions
  - interested/qualified handoff
  - activity events

Do not:

- rewrite the worker before the contract exists

### Phase 5: Move Truth Out Of Outreach SQLite

Do:

- migrate suppressions first
- migrate lifecycle next
- migrate messages and replies next
- migrate conversation linkage next
- leave SQLite only as worker-local cache/runtime store where necessary

Do not:

- keep critical state only in `outreach.db`

### Phase 6: Implement Acquisition -> Nurture Handoff

Do:

- make `interested` and `qualified` first-class transitions in core
- trigger nurture enrollment from core services
- add tests for duplicate/suppressed/bounced cases

Do not:

- implement handoff as ad hoc scripts that bypass canonical enrollment logic

### Phase 7: Consolidate Operator UI

Do:

- add acquisition workflows to the main web app
- add review queues
- add interested replies views
- add campaign control UI
- add unified timeline and analytics

Do not:

- keep two permanent operator consoles longer than necessary

### Phase 8: Finalize One-Deploy Stack

Do:

- centralize deployment assets in this repo
- build one Docker Compose deployment
- include web, API, worker, DB, persistent volumes
- add backup/restore workflows
- support Cloudflare-fronted production hosting

Do not:

- require fragmented manual deployments in the final state

## Verification Rules

Before claiming milestone completion, Codex must verify:

- no duplicate source-of-truth remains for the migrated concern
- lifecycle tests pass
- suppression tests pass
- integration tests for changed contracts pass
- mobile sync compatibility is preserved or intentionally migrated with docs
- acquisition worker compatibility is preserved or intentionally migrated with docs
- deployment artifacts still describe a coherent end state

Required test focus over the program:

- deduplication
- suppressions/unsubscribes
- lifecycle transitions
- business-card sync
- asset upload/storage
- outreach event ingestion
- acquisition-to-nurture handoff
- duplicate lead from multiple sources
- bounced/unsubscribed lead handling
- idempotent retries and reprocessing

## Deliverable Standard

Each substantial migration session should leave:

- code changes
- updated docs/contracts if behavior or architecture changed
- passing verification relevant to the changed scope
- a clear statement of what source of truth changed, if any

Final end-state definition:

- this repo is the sole source of truth for contacts, suppressions, enrollments, activity, and canonical messaging state
- CardScanner is a mobile client only
- outreach is a worker/service only
- operators primarily use one web app
- one Docker-based server deployment launches the platform stack
- one Cloudflare-pointed domain fronts the system

## Codex Launch Guidance

When running Codex for this migration, the preferred posture is:

- work from `/home/claudiu/projects/email-platform`
- inspect the two external source repos as needed
- update this repo first when introducing canonical contracts
- only then adapt the worker/mobile repos

Recommended workflow skill usage with oh-my-codex:

- use planning-first workflows for multi-session migration work
- use direct solo execution for bounded implementation phases after architecture is locked
- use parallel child agents only for independent, bounded slices such as:
  - core schema/service work
  - worker contract mapping analysis
  - mobile contract compatibility analysis
- do not use parallel agents to duplicate the same design work

## Immediate Program Start

If Codex is instructed to begin the migration without further clarification, start with:

1. create architecture and migration artifacts in this repo
2. implement the canonical core additions:
   - `Enrollment`
   - `Suppression`
   - `ActivityEvent`
   - `Conversation`
   - `Asset`
   - `LeadCapture`
3. lock lifecycle/status vocabulary with tests
4. formalize CardScanner server contract
5. formalize acquisition worker contract

That is the default first tranche of work.
