"""remove_pexels_api_key_from_settings

Revision ID: f6a71c2d3e4f
Revises: e5f82a1b98c3
Create Date: 2026-11-11 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a71c2d3e4f'
down_revision: Union[str, None] = 'e5f82a1b98c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate any remaining pexels_api_key to pixabay_api_key if pixabay is empty
    op.execute(
        "UPDATE system_settings SET pixabay_api_key = pexels_api_key "
        "WHERE (pixabay_api_key IS NULL OR pixabay_api_key = '') AND (pexels_api_key IS NOT NULL AND pexels_api_key != '')"
    )
    op.drop_column('system_settings', 'pexels_api_key')


def downgrade() -> None:
    op.add_column('system_settings', sa.Column('pexels_api_key', sa.Text(), nullable=True))
