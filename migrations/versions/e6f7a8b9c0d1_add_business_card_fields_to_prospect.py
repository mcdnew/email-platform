"""Add business card fields to prospect

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prospect', sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('website', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('linkedin', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('tags', sqlmodel.sql.sqltypes.AutoString(), nullable=True))        # JSON array as string
    op.add_column('prospect', sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('voice_notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True)) # JSON array [{text, recorded_at}]
    op.add_column('prospect', sa.Column('card_image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prospect', sa.Column('scanned_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('prospect', 'scanned_at')
    op.drop_column('prospect', 'card_image_path')
    op.drop_column('prospect', 'voice_notes')
    op.drop_column('prospect', 'notes')
    op.drop_column('prospect', 'tags')
    op.drop_column('prospect', 'linkedin')
    op.drop_column('prospect', 'address')
    op.drop_column('prospect', 'website')
    op.drop_column('prospect', 'phone')
