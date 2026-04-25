"""Shared lifecycle vocabulary and transition rules for the platform migration."""

from __future__ import annotations

CONTACT_LIFECYCLE_STAGES = (
    "captured",
    "pending_review",
    "ready_for_outreach",
    "outreach_active",
    "awaiting_reply",
    "interested",
    "qualified",
    "nurture_active",
    "opportunity",
    "customer",
    "lost",
    "archived",
)

CONTACT_BLOCKING_FLAGS = (
    "unsubscribed",
    "bounced",
    "do_not_contact",
    "invalid_email",
    "duplicate",
    "blocked",
)

ENROLLMENT_STATES = (
    "draft",
    "active",
    "paused",
    "completed",
    "cancelled",
    "failed",
)

CONVERSATION_STATES = (
    "open",
    "waiting_on_us",
    "waiting_on_contact",
    "closed",
    "suppressed",
)

OUTREACH_REPLY_INTENTS = (
    "INTERESTED",
    "QUESTION",
    "NOT_NOW",
    "UNSUBSCRIBE",
    "OTHER",
)

LEAD_CAPTURE_REVIEW_STATES = (
    "pending_review",
    "approved",
    "rejected",
    "linked",
)

SUPPRESSION_SCOPES = (
    "global",
    "campaign",
    "channel",
)

ALLOWED_CONTACT_STAGE_TRANSITIONS = {
    "captured": {"pending_review", "ready_for_outreach", "archived"},
    "pending_review": {"ready_for_outreach", "lost", "archived"},
    "ready_for_outreach": {"outreach_active", "nurture_active", "lost", "archived"},
    "outreach_active": {"awaiting_reply", "interested", "qualified", "lost", "archived"},
    "awaiting_reply": {"interested", "qualified", "nurture_active", "lost", "archived"},
    "interested": {"qualified", "nurture_active", "opportunity", "lost", "archived"},
    "qualified": {"nurture_active", "opportunity", "lost", "archived"},
    "nurture_active": {"opportunity", "customer", "lost", "archived"},
    "opportunity": {"customer", "lost", "archived"},
    "customer": {"archived"},
    "lost": {"archived"},
    "archived": set(),
}


def is_known_contact_stage(stage: str) -> bool:
    return stage in CONTACT_LIFECYCLE_STAGES


def can_transition_contact_stage(current: str, target: str) -> bool:
    if current == target:
        return True
    if not is_known_contact_stage(current) or not is_known_contact_stage(target):
        return False
    return target in ALLOWED_CONTACT_STAGE_TRANSITIONS[current]


def map_outreach_reply_intent_to_stage(intent: str, current: str | None = None) -> str | None:
    normalized = (intent or "").upper()
    if normalized == "INTERESTED":
        return "interested"
    if normalized in {"QUESTION", "NOT_NOW", "OTHER"}:
        return "awaiting_reply"
    if normalized == "UNSUBSCRIBE":
        return current
    return None
