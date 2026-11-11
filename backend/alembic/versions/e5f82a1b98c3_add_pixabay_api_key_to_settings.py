"""add_pixabay_api_key_to_settings

Revision ID: e5f82a1b98c3
Revises: d4e71fba9901
Create Date: 2026-11-11 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f82a1b98c3'
down_revision: Union[str, None] = 'd4e71fba9901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('system_settings', sa.Column('pixabay_api_key', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('system_settings', 'pixabay_api_key')
