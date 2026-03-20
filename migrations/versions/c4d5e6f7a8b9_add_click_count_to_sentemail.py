"""add click_count to sentemail

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sentemail', sa.Column('click_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('sentemail', 'click_count')
