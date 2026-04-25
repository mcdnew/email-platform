"""Add platform foundation tables and prospect lifecycle fields

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-25 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "prospect",
        sa.Column("lifecycle_stage", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="captured"),
    )
    op.add_column(
        "prospect",
        sa.Column("source_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="manual"),
    )
    op.add_column("prospect", sa.Column("source_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("prospect", sa.Column("owner", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("prospect", sa.Column("last_contacted_at", sa.DateTime(), nullable=True))
    op.add_column("prospect", sa.Column("interested_at", sa.DateTime(), nullable=True))
    op.add_column("prospect", sa.Column("qualified_at", sa.DateTime(), nullable=True))
    op.create_index("ix_prospect_lifecycle_stage", "prospect", ["lifecycle_stage"], unique=False)
    op.create_index("ix_prospect_source_type", "prospect", ["source_type"], unique=False)

    op.create_table(
        "enrollment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("campaign_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("entered_at", sa.DateTime(), nullable=False),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("exit_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.ForeignKeyConstraint(["sequence_id"], ["sequence.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrollment_campaign_key", "enrollment", ["campaign_key"], unique=False)
    op.create_index("ix_enrollment_status", "enrollment", ["status"], unique=False)

    op.create_table(
        "suppression",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("scope", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("channel", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("campaign_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppression_campaign_key", "suppression", ["campaign_key"], unique=False)
    op.create_index("ix_suppression_email", "suppression", ["email"], unique=False)
    op.create_index("ix_suppression_scope", "suppression", ["scope"], unique=False)

    op.create_table(
        "activityevent",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=True),
        sa.Column("sequence_id", sa.Integer(), nullable=True),
        sa.Column("campaign_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_module", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("payload_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.ForeignKeyConstraint(["sequence_id"], ["sequence.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activityevent_event_type", "activityevent", ["event_type"], unique=False)
    op.create_index("ix_activityevent_source_module", "activityevent", ["source_module"], unique=False)

    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=False),
        sa.Column("campaign_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("channel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("provider_thread_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_campaign_key", "conversation", ["campaign_key"], unique=False)
    op.create_index("ix_conversation_provider_thread_id", "conversation", ["provider_thread_id"], unique=False)
    op.create_index("ix_conversation_state", "conversation", ["state"], unique=False)

    op.create_table(
        "asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("storage_backend", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("storage_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("original_filename", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_asset_type", "asset", ["asset_type"], unique=False)

    op.create_table(
        "leadcapture",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospect_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("review_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("raw_payload_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("normalized_payload_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("external_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prospect_id"], ["prospect.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leadcapture_external_ref", "leadcapture", ["external_ref"], unique=False)
    op.create_index("ix_leadcapture_review_status", "leadcapture", ["review_status"], unique=False)
    op.create_index("ix_leadcapture_source_type", "leadcapture", ["source_type"], unique=False)

    op.alter_column("prospect", "lifecycle_stage", server_default=None)
    op.alter_column("prospect", "source_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_leadcapture_source_type", table_name="leadcapture")
    op.drop_index("ix_leadcapture_review_status", table_name="leadcapture")
    op.drop_index("ix_leadcapture_external_ref", table_name="leadcapture")
    op.drop_table("leadcapture")

    op.drop_index("ix_asset_asset_type", table_name="asset")
    op.drop_table("asset")

    op.drop_index("ix_conversation_state", table_name="conversation")
    op.drop_index("ix_conversation_provider_thread_id", table_name="conversation")
    op.drop_index("ix_conversation_campaign_key", table_name="conversation")
    op.drop_table("conversation")

    op.drop_index("ix_activityevent_source_module", table_name="activityevent")
    op.drop_index("ix_activityevent_event_type", table_name="activityevent")
    op.drop_table("activityevent")

    op.drop_index("ix_suppression_scope", table_name="suppression")
    op.drop_index("ix_suppression_email", table_name="suppression")
    op.drop_index("ix_suppression_campaign_key", table_name="suppression")
    op.drop_table("suppression")

    op.drop_index("ix_enrollment_status", table_name="enrollment")
    op.drop_index("ix_enrollment_campaign_key", table_name="enrollment")
    op.drop_table("enrollment")

    op.drop_index("ix_prospect_source_type", table_name="prospect")
    op.drop_index("ix_prospect_lifecycle_stage", table_name="prospect")
    op.drop_column("prospect", "qualified_at")
    op.drop_column("prospect", "interested_at")
    op.drop_column("prospect", "last_contacted_at")
    op.drop_column("prospect", "owner")
    op.drop_column("prospect", "source_ref")
    op.drop_column("prospect", "source_type")
    op.drop_column("prospect", "lifecycle_stage")
