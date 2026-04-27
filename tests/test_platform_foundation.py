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
    SequenceStep,
    ScheduledEmail,
    SentEmail,
    EmailTemplate,
    Enrollment,
    Suppression,
    ActivityEvent,
    Conversation,
    Asset,
    LeadCapture,
    WorkerCampaignSnapshot,
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


def test_get_prospect_returns_single_prospect(client, db):
    prospect = Prospect(name="Direct Lookup", email="lookup@example.com", company="Lookup Co", title="Owner")
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    resp = client.get(f"/prospects/{prospect.id}")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == prospect.id
    assert payload["email"] == "lookup@example.com"
    assert payload["company"] == "Lookup Co"


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


def test_outreach_discovery_ingest_creates_prospects_and_lead_captures(client, db):
    resp = client.post(
        "/integrations/outreach/discoveries",
        json={
            "campaign_key": "acquire:lumber",
            "approval_required": True,
            "leads": [
                {
                    "name": "Dana Discovery",
                    "email": "dana@example.com",
                    "company": "North Mill",
                    "title": "Owner",
                    "fact": "Expanding yard in 2026",
                    "external_ref": "disc-1",
                },
                {
                    "name": "No Email Lead",
                    "company": "Unknown Timber",
                    "external_ref": "disc-2",
                },
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created_or_updated"] == 1
    assert data["lead_captures_recorded"] == 2

    prospect = db.exec(select(Prospect).where(Prospect.email == "dana@example.com")).first()
    assert prospect is not None
    assert prospect.source_type == "web_discovery"
    assert prospect.lifecycle_stage == "pending_review"

    captures = db.exec(select(LeadCapture).order_by(LeadCapture.external_ref)).all()
    assert len(captures) == 2
    assert captures[0].prospect_id == prospect.id
    assert captures[1].prospect_id is None

    event = db.exec(select(ActivityEvent).where(ActivityEvent.prospect_id == prospect.id)).first()
    assert event is not None
    assert event.event_type == "acquire.discovery_ingested"


def test_outreach_discovery_check_detects_existing_email_and_company(client, db):
    prospect = Prospect(
        name="Existing User",
        email="existing@example.com",
        company="North Mill Ltd.",
        source_type="web_discovery",
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    email_resp = client.post(
        "/integrations/outreach/discovery-check",
        json={"campaign_key": "acquire:lumber", "email": "existing@example.com", "company": "Other Co"},
    )
    assert email_resp.status_code == 200
    assert email_resp.json()["classification"] == "duplicate_acquisition_contact"

    company_resp = client.post(
        "/integrations/outreach/discovery-check",
        json={"campaign_key": "acquire:lumber", "company": "North Mill Limited", "website": "https://northmill.test"},
    )
    assert company_resp.status_code == 200
    assert company_resp.json()["classification"] == "duplicate_acquisition_company"


def test_outreach_discovery_ingest_links_known_company_without_new_pending_review(client, db):
    prospect = Prospect(
        name="Known Company Owner",
        email="owner@northmill.test",
        company="North Mill Ltd.",
        source_type="web_discovery",
        lifecycle_stage="ready_for_outreach",
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    resp = client.post(
        "/integrations/outreach/discoveries",
        json={
            "campaign_key": "acquire:lumber",
            "approval_required": True,
            "leads": [
                {
                    "name": "Fresh Contact",
                    "email": None,
                    "company": "North Mill Limited",
                    "title": "Operations Director",
                    "website": "https://northmill.test",
                    "external_ref": "disc-known-company",
                }
            ],
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created_or_updated"] == 0

    capture = db.exec(select(LeadCapture).where(LeadCapture.external_ref == "disc-known-company")).one()
    assert capture.review_status == "linked"
    assert capture.prospect_id == prospect.id

    duplicate_event = db.exec(
        select(ActivityEvent).where(ActivityEvent.event_type == "acquire.discovery_duplicate_skipped")
    ).one()
    assert duplicate_event.prospect_id == prospect.id


def test_outreach_message_and_reply_ingest_update_conversation_and_suppression(client, db):
    prospect = Prospect(
        name="Reply User",
        email="reply@example.com",
        lifecycle_stage="ready_for_outreach",
        source_type="web_discovery",
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    sent_resp = client.post(
        "/integrations/outreach/messages/sent",
        json={
            "prospect_id": prospect.id,
            "campaign_key": "acquire:lumber",
            "gmail_thread_id": "thread-777",
            "sequence_step": 1,
            "subject": "Quick question",
            "body": "Hello there",
        },
    )
    assert sent_resp.status_code == 200

    db.refresh(prospect)
    assert prospect.lifecycle_stage == "awaiting_reply"
    assert prospect.last_contacted_at is not None

    reply_resp = client.post(
        "/integrations/outreach/replies",
        json={
            "prospect_id": prospect.id,
            "campaign_key": "acquire:lumber",
            "intent": "INTERESTED",
            "body": "Tell me more",
            "gmail_thread_id": "thread-777",
            "incoming_message_id": "msg-1",
            "from_email": "reply@example.com",
        },
    )
    assert reply_resp.status_code == 200
    reply_data = reply_resp.json()
    assert reply_data["lifecycle_stage"] == "interested"

    db.refresh(prospect)
    assert prospect.interested_at is not None

    conversation = db.exec(select(Conversation).where(Conversation.prospect_id == prospect.id)).first()
    assert conversation is not None
    assert conversation.provider_thread_id == "thread-777"
    assert conversation.state == "waiting_on_us"

    events = db.exec(select(ActivityEvent).where(ActivityEvent.prospect_id == prospect.id)).all()
    event_types = {event.event_type for event in events}
    assert "acquire.message_sent" in event_types
    assert "acquire.reply_received" in event_types

    unsubscribe_resp = client.post(
        "/integrations/outreach/replies",
        json={
            "prospect_id": prospect.id,
            "campaign_key": "acquire:lumber",
            "intent": "UNSUBSCRIBE",
            "body": "Please stop",
            "gmail_thread_id": "thread-777",
        },
    )
    assert unsubscribe_resp.status_code == 200

    db.refresh(prospect)
    assert prospect.unsubscribed is True
    suppression = db.exec(select(Suppression).where(Suppression.email == prospect.email)).first()
    assert suppression is not None
    assert suppression.reason == "unsubscribe"


def test_sequence_assignment_creates_enrollment_and_handoff_promotes_to_nurture(client, db):
    prospect = Prospect(
        name="Nurture User",
        email="nurture@example.com",
        lifecycle_stage="qualified",
        source_type="web_discovery",
    )
    sequence = Sequence(name="Welcome Nurture")
    db.add(prospect)
    db.add(sequence)
    db.commit()
    db.refresh(prospect)
    db.refresh(sequence)

    template_resp = client.post("/templates", json={"name": "Intro", "subject": "Hi", "body": "Hello"})
    assert template_resp.status_code == 200
    template_id = template_resp.json()["id"]

    step = SequenceStep(sequence_id=sequence.id, template_id=template_id, delay_days=0)
    db.add(step)
    db.commit()

    handoff_resp = client.post(
        "/integrations/outreach/handoffs/nurture",
        json={
            "prospect_id": prospect.id,
            "campaign_key": "acquire:lumber",
            "sequence_id": sequence.id,
            "qualified": True,
            "notes": "Warm handoff from outreach",
        },
    )
    assert handoff_resp.status_code == 200
    handoff = handoff_resp.json()
    assert handoff["lifecycle_stage"] == "nurture_active"

    db.refresh(prospect)
    assert prospect.lifecycle_stage == "nurture_active"
    assert prospect.qualified_at is not None
    assert "Warm handoff from outreach" in (prospect.notes or "")

    enrollment = db.exec(select(Enrollment).where(Enrollment.prospect_id == prospect.id)).first()
    assert enrollment is not None
    assert enrollment.sequence_id == sequence.id
    assert enrollment.status == "active"
    assert enrollment.campaign_key == "acquire:lumber"

    scheduled = db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == prospect.id)).all()
    assert len(scheduled) == 1

    handoff_event = db.exec(
        select(ActivityEvent).where(
            ActivityEvent.prospect_id == prospect.id,
            ActivityEvent.event_type == "acquire.handoff_to_nurture",
        )
    ).first()
    assert handoff_event is not None


def test_lead_capture_review_queue_and_approval(client, db):
    ingest = client.post(
        "/integrations/outreach/discoveries",
        json={
            "campaign_key": "acquire:lumber",
            "approval_required": True,
            "leads": [
                {
                    "name": "Queue Lead",
                    "email": "queue@example.com",
                    "company": "Queue Co",
                    "external_ref": "queue-1",
                }
            ],
        },
    )
    assert ingest.status_code == 200

    queue_resp = client.get("/lead-captures?review_status=pending_review&source_type=web_discovery")
    assert queue_resp.status_code == 200
    items = queue_resp.json()
    assert len(items) == 1
    capture_id = items[0]["id"]

    review_resp = client.post(
        f"/lead-captures/{capture_id}/review",
        json={"review_status": "approved", "notes": "Operator approved"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["prospect_id"] is not None

    capture = db.get(LeadCapture, capture_id)
    assert capture.review_status == "approved"
    assert capture.reviewed_at is not None

    prospect = db.exec(select(Prospect).where(Prospect.email == "queue@example.com")).first()
    assert prospect is not None
    assert prospect.lifecycle_stage == "ready_for_outreach"
    assert "Operator approved" in (prospect.notes or "")


def test_lead_capture_review_can_promote_capture_without_email_to_prospect(client, db):
    capture = LeadCapture(
        source_type="web_discovery",
        review_status="pending_review",
        normalized_payload_json=json.dumps({
            "name": "Julien Renaud",
            "email": None,
            "company": "Henry Timber",
            "title": None,
        }),
        external_ref="tallyexpress-dealers:Henry Timber",
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    resp = client.post(
        f"/lead-captures/{capture.id}/review",
        json={
            "review_status": "approved",
            "email": "julien.renaud@example.com",
            "title": "Commercial Director",
            "notes": "Email verified manually",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["prospect_id"] is not None

    db.refresh(capture)
    assert capture.prospect_id is not None

    prospect = db.get(Prospect, capture.prospect_id)
    assert prospect is not None
    assert prospect.email == "julien.renaud@example.com"
    assert prospect.name == "Julien Renaud"
    assert prospect.company == "Henry Timber"
    assert prospect.title == "Commercial Director"
    assert prospect.lifecycle_stage == "ready_for_outreach"


def test_activity_events_and_conversations_list_endpoints(client, db):
    prospect = Prospect(name="Event User", email="event@example.com", lifecycle_stage="interested")
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    event = ActivityEvent(
        prospect_id=prospect.id,
        campaign_key="acquire:lumber",
        event_type="acquire.reply_received",
        source_module="acquire",
        payload_json='{"intent":"INTERESTED"}',
    )
    conversation = Conversation(
        prospect_id=prospect.id,
        campaign_key="acquire:lumber",
        channel="gmail",
        provider_thread_id="thread-abc",
        state="waiting_on_us",
    )
    db.add(event)
    db.add(conversation)
    db.commit()

    events_resp = client.get("/activity-events?source_module=acquire&campaign_key=acquire:lumber")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "acquire.reply_received"

    conv_resp = client.get("/conversations?channel=gmail&state=waiting_on_us")
    assert conv_resp.status_code == 200
    conversations = conv_resp.json()
    assert len(conversations) == 1
    assert conversations[0]["provider_thread_id"] == "thread-abc"


def test_partial_prospect_update_supports_unsubscribe_toggle(client, db):
    prospect = Prospect(name="Toggle User", email="toggle@example.com", unsubscribed=False)
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    resp = client.put(f"/prospects/{prospect.id}", json={"unsubscribed": True})

    assert resp.status_code == 200
    db.refresh(prospect)
    assert prospect.unsubscribed is True


def test_delete_prospect_handles_gathered_lead_relations(client, db):
    prospect = Prospect(
        name="Delete Me",
        email="delete@example.com",
        lifecycle_stage="interested",
        notes="Important history",
        source_type="web_discovery",
    )
    sequence = Sequence(name="Cleanup Sequence")
    template = EmailTemplate(name="Cleanup Template", subject="Hi", body="Body")
    db.add(prospect)
    db.add(sequence)
    db.add(template)
    db.commit()
    db.refresh(prospect)
    db.refresh(sequence)
    db.refresh(template)

    db.add(ScheduledEmail(
        prospect_id=prospect.id,
        template_id=template.id,
        sequence_id=sequence.id,
        send_at=prospect.created_at,
        status="pending",
    ))
    db.add(SentEmail(
        to=prospect.email,
        subject="Subject",
        body="Body",
        sent_at=prospect.created_at,
        status="sent",
        prospect_id=prospect.id,
        sequence_id=sequence.id,
    ))
    db.add(Enrollment(prospect_id=prospect.id, sequence_id=sequence.id, campaign_key="acquire:test", status="active"))
    db.add(Suppression(prospect_id=prospect.id, email=prospect.email, scope="global", reason="unsubscribe"))
    db.add(ActivityEvent(prospect_id=prospect.id, event_type="acquire.reply_received", source_module="acquire"))
    db.add(Conversation(prospect_id=prospect.id, campaign_key="acquire:test", channel="gmail", provider_thread_id="thread-del", state="waiting_on_us"))
    db.add(Asset(prospect_id=prospect.id, asset_type="business_card_image", storage_backend="local", storage_path="cards/delete.jpg"))
    db.add(LeadCapture(prospect_id=prospect.id, source_type="web_discovery", review_status="approved", external_ref="acquire:test:1"))
    db.commit()
    prospect_id = prospect.id
    prospect_email = prospect.email

    resp = client.delete(f"/prospects/{prospect_id}")

    assert resp.status_code == 200
    db.expire_all()
    assert db.get(Prospect, prospect_id) is None
    assert db.exec(select(Enrollment).where(Enrollment.prospect_id == prospect_id)).all() == []
    assert db.exec(select(Conversation).where(Conversation.prospect_id == prospect_id)).all() == []
    assert db.exec(select(Asset).where(Asset.prospect_id == prospect_id)).all() == []
    assert db.exec(select(ScheduledEmail).where(ScheduledEmail.prospect_id == prospect_id)).all() == []
    detached_sent = db.exec(select(SentEmail).where(SentEmail.to == prospect_email)).one()
    detached_suppression = db.exec(select(Suppression).where(Suppression.email == prospect_email)).one()
    detached_event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.reply_received")).one()
    detached_capture = db.exec(select(LeadCapture).where(LeadCapture.external_ref == "acquire:test:1")).one()
    assert detached_sent.prospect_id is None
    assert detached_suppression.prospect_id is None
    assert detached_event.prospect_id is None
    assert detached_capture.prospect_id is None


def test_prospect_lifecycle_action_updates_stage_and_closes_conversations(client, db):
    prospect = Prospect(name="Lifecycle User", email="life@example.com", lifecycle_stage="interested")
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    conversation = Conversation(
        prospect_id=prospect.id,
        campaign_key="acquire:lumber",
        channel="gmail",
        provider_thread_id="thread-life",
        state="waiting_on_us",
    )
    db.add(conversation)
    db.commit()

    qualify_resp = client.post(
        f"/prospects/{prospect.id}/lifecycle",
        json={"target_stage": "qualified", "notes": "Sales-ready"},
    )
    assert qualify_resp.status_code == 200
    db.refresh(prospect)
    assert prospect.lifecycle_stage == "qualified"
    assert prospect.qualified_at is not None
    assert "Sales-ready" in (prospect.notes or "")

    lost_resp = client.post(
        f"/prospects/{prospect.id}/lifecycle",
        json={"target_stage": "lost"},
    )
    assert lost_resp.status_code == 200
    db.refresh(prospect)
    assert prospect.lifecycle_stage == "lost"

    db.refresh(conversation)
    assert conversation.state == "closed"


def test_acquisition_campaign_summary_aggregates_core_records(client, db):
    p1 = Prospect(name="One", email="one@example.com", lifecycle_stage="interested", source_ref="acquire:lumber:1")
    p2 = Prospect(name="Two", email="two@example.com", lifecycle_stage="ready_for_outreach", source_ref="acquire:lumber:2")
    db.add(p1)
    db.add(p2)
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    db.add(LeadCapture(source_type="web_discovery", review_status="pending_review", external_ref="acquire:lumber:1"))
    db.add(ActivityEvent(prospect_id=p1.id, campaign_key="acquire:lumber", event_type="acquire.reply_received", source_module="acquire"))
    db.add(Conversation(prospect_id=p1.id, campaign_key="acquire:lumber", channel="gmail", provider_thread_id="thread-1", state="waiting_on_us"))
    db.commit()

    resp = client.get("/acquire/campaigns/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["campaign_key"] == "acquire:lumber"
    assert data[0]["pending_review"] == 1
    assert data[0]["interested"] == 1
    assert data[0]["conversations"] == 1
    assert data[0]["recent_events"] == 1


def test_worker_campaigns_proxy_returns_json(client, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "name": "alpha",
                "product": "TallyExpress",
                "language": "en",
                "discover_prompt": "yards",
                "discover_count": 15,
                "approval_required": True,
                "active": 2,
                "interested": 1,
                "emails_sent": 8,
                "running": False,
                "started": None,
                "error": None,
            }]

    def fake_get(url: str, timeout: int):
        assert url.endswith("/api/campaigns")
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "get", fake_get)
    resp = client.get("/acquire/worker/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["name"] == "alpha"


def test_worker_campaign_create_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 201
        text = ""

        def json(self):
            return {"message": "created", "campaign": "alpha"}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns")
        assert json["name"] == "alpha"
        assert "config" in json
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post("/acquire/worker/campaigns", json={"name": "alpha", "config": {"campaign": {"product": "Updated"}}})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["campaign"] == "alpha"

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_campaign_created")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_archive_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"message": "saved", "campaign": "alpha", "archived": True}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/archive")
        assert json == {"archived": True}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post("/acquire/worker/campaigns/alpha/archive", json={"archived": True})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["archived"] is True

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_campaign_archived")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_delete_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"message": "deleted", "campaign": "alpha"}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/delete")
        assert json == {"confirm_name": "alpha"}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post("/acquire/worker/campaigns/alpha/delete", json={"confirm_name": "alpha"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["campaign"] == "alpha"

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_campaign_deleted")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_run_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"message": "started", "campaign": "alpha", "dry_run": True}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/run")
        assert json == {"dry_run": True}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post("/acquire/worker/campaigns/alpha/run", json={"dry_run": True})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["campaign"] == "alpha"

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_run_requested")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_discover_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"message": "started", "campaign": "alpha", "dry_run": True, "count": 12}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/discover")
        assert json == {"dry_run": True, "count": 12}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post("/acquire/worker/campaigns/alpha/discover", json={"dry_run": True, "count": 12})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["campaign"] == "alpha"
    assert payload["count"] == 12

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_discovery_requested")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_detail_proxy_returns_payload(client, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "name": "alpha",
                "config": {"campaign": {"product": "TallyExpress"}, "sequence": [{"day": 0, "type": "initial"}]},
                "stats": {"emails_sent": 8},
                "running": False,
                "started": None,
                "error": None,
            }

    def fake_get(url: str, timeout: int):
        assert url.endswith("/api/campaigns/alpha")
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "get", fake_get)
    resp = client.get("/acquire/worker/campaigns/alpha")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["name"] == "alpha"
    assert payload["config"]["campaign"]["product"] == "TallyExpress"


def test_worker_campaign_activity_proxy_returns_payload(client, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"entries": [{"id": 1, "ts": "2026-04-27T00:00:00Z", "campaign": "alpha", "level": "info", "message": "Cycle completed"}], "max_id": 1}

    def fake_get(url: str, params: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/activity")
        assert params == {"since_id": 0, "limit": 100}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "get", fake_get)
    resp = client.get("/acquire/worker/campaigns/alpha/activity")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["max_id"] == 1
    assert payload["entries"][0]["message"] == "Cycle completed"


def test_worker_campaign_traces_proxy_returns_payload(client, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"entries": [{"id": 1, "ts": "2026-04-27T00:00:00Z", "campaign": "alpha", "run_id": "run-1", "kind": "discover", "event": "model_request", "payload": "{}"}]}

    def fake_get(url: str, params: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha/traces")
        assert params == {"limit": 100, "run_id": None}
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "get", fake_get)
    resp = client.get("/acquire/worker/campaigns/alpha/traces")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload[0]["event"] == "model_request"


def test_worker_campaign_update_proxy_records_activity(client, db, monkeypatch):
    import app.main as app_main

    class DummyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"message": "saved", "campaign": "alpha"}

    def fake_post(url: str, json: dict, timeout: int):
        assert url.endswith("/api/campaigns/alpha")
        assert "config" in json
        assert timeout == 5
        return DummyResponse()

    monkeypatch.setattr(app_main.requests, "post", fake_post)
    resp = client.post(
        "/acquire/worker/campaigns/alpha",
        json={"config": {"campaign": {"product": "Updated"}}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["campaign"] == "alpha"

    event = db.exec(select(ActivityEvent).where(ActivityEvent.event_type == "acquire.worker_campaign_updated")).first()
    assert event is not None
    assert event.campaign_key == "alpha"


def test_worker_campaign_list_falls_back_to_cached_snapshots(client, db, monkeypatch):
    db.add(WorkerCampaignSnapshot(
        name="alpha",
        product="TallyExpress",
        language="en",
        discover_prompt="yards",
        discover_count=12,
        approval_required=True,
        active=2,
        interested=1,
        emails_sent=9,
        running=False,
        config_json='{"campaign":{"product":"TallyExpress"}}',
        stats_json='{"emails_sent":9}',
    ))
    db.commit()

    import app.main as app_main

    def failing_get(url: str, timeout: int):
        raise RuntimeError("worker down")

    monkeypatch.setattr(app_main.requests, "get", failing_get)
    resp = client.get("/acquire/worker/campaigns")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "alpha"


def test_worker_campaign_detail_falls_back_to_cached_snapshot(client, db, monkeypatch):
    db.add(WorkerCampaignSnapshot(
        name="alpha",
        product="TallyExpress",
        language="en",
        discover_prompt="yards",
        discover_count=12,
        approval_required=True,
        active=2,
        interested=1,
        emails_sent=9,
        running=False,
        config_json='{"campaign":{"product":"TallyExpress"}}',
        stats_json='{"emails_sent":9}',
    ))
    db.commit()

    import app.main as app_main

    def failing_get(url: str, timeout: int):
        raise RuntimeError("worker down")

    monkeypatch.setattr(app_main.requests, "get", failing_get)
    resp = client.get("/acquire/worker/campaigns/alpha")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["name"] == "alpha"
    assert payload["config"]["campaign"]["product"] == "TallyExpress"
