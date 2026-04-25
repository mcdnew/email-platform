import io
import json

from sqlalchemy import inspect
from sqlmodel import select

from app.lifecycle import (
    CONTACT_LIFECYCLE_STAGES,
    ENROLLMENT_STATES,
    CONVERSATION_STATES,
    can_transition_contact_stage,
)
from app.models import (
    Prospect,
    Sequence,
    Enrollment,
    Suppression,
    ActivityEvent,
    Conversation,
    Asset,
    LeadCapture,
)


def test_platform_foundation_tables_exist(db):
    inspector = inspect(db.get_bind())
    tables = set(inspector.get_table_names())
    assert {"enrollment", "suppression", "activityevent", "conversation", "asset", "leadcapture"} <= tables


def test_prospect_platform_defaults(db):
    prospect = Prospect(name="Alice", email="alice@example.com")
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    assert prospect.lifecycle_stage == "captured"
    assert prospect.source_type == "manual"
    assert prospect.source_ref is None
    assert prospect.owner is None
    assert prospect.last_contacted_at is None
    assert prospect.interested_at is None
    assert prospect.qualified_at is None


def test_contact_lifecycle_transition_rules():
    assert "captured" in CONTACT_LIFECYCLE_STAGES
    assert "active" in ENROLLMENT_STATES
    assert "waiting_on_contact" in CONVERSATION_STATES

    assert can_transition_contact_stage("captured", "pending_review")
    assert can_transition_contact_stage("ready_for_outreach", "outreach_active")
    assert can_transition_contact_stage("qualified", "opportunity")

    assert not can_transition_contact_stage("captured", "customer")
    assert not can_transition_contact_stage("archived", "captured")
    assert not can_transition_contact_stage("unknown", "captured")


def test_foundation_models_can_persist_together(db):
    prospect = Prospect(name="Bob", email="bob@example.com", lifecycle_stage="pending_review", source_type="business_card")
    sequence = Sequence(name="Warm Intro")
    db.add(prospect)
    db.add(sequence)
    db.commit()
    db.refresh(prospect)
    db.refresh(sequence)

    enrollment = Enrollment(
        prospect_id=prospect.id,
        sequence_id=sequence.id,
        campaign_key="nurture:welcome",
        status="active",
        current_step=1,
    )
    suppression = Suppression(
        prospect_id=prospect.id,
        email=prospect.email,
        scope="campaign",
        reason="manual",
        campaign_key="acquire:lumber",
    )
    event = ActivityEvent(
        prospect_id=prospect.id,
        sequence_id=sequence.id,
        event_type="contact.captured",
        source_module="capture",
        payload_json='{"source":"business_card"}',
    )
    conversation = Conversation(
        prospect_id=prospect.id,
        campaign_key="acquire:lumber",
        channel="gmail",
        provider_thread_id="thread-123",
        state="open",
    )
    asset = Asset(
        prospect_id=prospect.id,
        asset_type="business_card_image",
        storage_backend="local",
        storage_path="card_images/bob.jpg",
        content_type="image/jpeg",
    )
    lead_capture = LeadCapture(
        prospect_id=prospect.id,
        source_type="business_card",
        review_status="linked",
        raw_payload_json='{"ocr":"Bob"}',
        normalized_payload_json='{"email":"bob@example.com"}',
        external_ref="scan-001",
    )

    db.add(enrollment)
    db.add(suppression)
    db.add(event)
    db.add(conversation)
    db.add(asset)
    db.add(lead_capture)
    db.commit()

    assert db.exec(select(Enrollment)).one().campaign_key == "nurture:welcome"
    assert db.exec(select(Suppression)).one().scope == "campaign"
    assert db.exec(select(ActivityEvent)).one().source_module == "capture"
    assert db.exec(select(Conversation)).one().provider_thread_id == "thread-123"
    assert db.exec(select(Asset)).one().asset_type == "business_card_image"
    assert db.exec(select(LeadCapture)).one().external_ref == "scan-001"


def test_business_card_upsert_creates_lead_capture_and_activity(client, db):
    resp = client.post(
        "/prospects/upsert",
        json={
            "name": "Alice Card",
            "email": "alice.card@example.com",
            "company": "Acme",
            "phone": "+34123456",
            "tags": ["expo", "priority"],
            "notes": "Met at booth",
            "scanned_at": "2026-04-25T10:00:00",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["action"] == "created"

    prospect = db.get(Prospect, payload["id"])
    assert prospect is not None
    assert prospect.source_type == "business_card"
    assert prospect.lifecycle_stage == "captured"

    capture = db.exec(select(LeadCapture).where(LeadCapture.prospect_id == prospect.id)).first()
    assert capture is not None
    assert capture.source_type == "business_card"
    assert capture.review_status == "linked"
    normalized = json.loads(capture.normalized_payload_json)
    assert normalized["email"] == "alice.card@example.com"

    event = db.exec(select(ActivityEvent).where(ActivityEvent.prospect_id == prospect.id)).first()
    assert event is not None
    assert event.event_type == "capture.upserted"
    assert event.source_module == "capture"


def test_asset_upload_endpoints_create_asset_records(client, db, tmp_path, monkeypatch):
    import app.main as app_main

    monkeypatch.setattr(app_main, "CARD_IMAGES_DIR", str(tmp_path / "card_images"))
    monkeypatch.setattr(app_main, "VOICE_NOTES_DIR", str(tmp_path / "voice_notes"))

    prospect = Prospect(name="Asset User", email="asset@example.com")
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    img_resp = client.post(
        f"/prospects/{prospect.id}/card-image",
        files={"file": ("card.jpg", io.BytesIO(b"fake-jpg"), "image/jpeg")},
    )
    assert img_resp.status_code == 200
    img_path = img_resp.json()["path"]
    assert img_path.startswith(str(tmp_path))

    voice_resp = client.post(
        f"/prospects/{prospect.id}/voice-note",
        files={"file": ("note.m4a", io.BytesIO(b"fake-audio"), "audio/mp4")},
    )
    assert voice_resp.status_code == 200
    voice_path = voice_resp.json()["path"]
    assert voice_path.startswith(str(tmp_path))

    assets = db.exec(select(Asset).where(Asset.prospect_id == prospect.id)).all()
    asset_types = {a.asset_type for a in assets}
    assert asset_types == {"business_card_image", "voice_note_audio"}

    events = db.exec(select(ActivityEvent).where(ActivityEvent.prospect_id == prospect.id)).all()
    assert sum(1 for event in events if event.event_type == "asset.uploaded") == 2
