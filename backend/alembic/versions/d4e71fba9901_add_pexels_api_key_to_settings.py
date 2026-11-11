"""add_pexels_api_key_to_settings

Revision ID: d4e71fba9901
Revises: c3d60dce0224
Create Date: 2026-11-11 04:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e71fba9901'
down_revision: Union[str, None] = 'c3d60dce0224'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('system_settings', sa.Column('pexels_api_key', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('system_settings', 'pexels_api_key')
