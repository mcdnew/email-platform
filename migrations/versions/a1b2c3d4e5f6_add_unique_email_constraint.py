"""Add unique constraint on prospect.email

Revision ID: a1b2c3d4e5f6
Revises: 5709abcc18d4
Create Date: 2026-03-20 01:40:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5709abcc18d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_prospect_email', 'prospect', ['email'])


def downgrade() -> None:
    op.drop_constraint('uq_prospect_email', 'prospect', type_='unique')
