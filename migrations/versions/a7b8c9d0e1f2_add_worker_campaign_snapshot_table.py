"""Add worker campaign snapshot table

Revision ID: a7b8c9d0e1f2
Revises: f7a8b9c0d1e2
Create Date: 2026-04-26 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workercampaignsnapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("product", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("discover_prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("discover_count", sa.Integer(), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False),
        sa.Column("interested", sa.Integer(), nullable=False),
        sa.Column("emails_sent", sa.Integer(), nullable=False),
        sa.Column("running", sa.Boolean(), nullable=False),
        sa.Column("started", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("config_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("stats_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workercampaignsnapshot_name", "workercampaignsnapshot", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workercampaignsnapshot_name", table_name="workercampaignsnapshot")
    op.drop_table("workercampaignsnapshot")
