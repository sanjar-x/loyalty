"""merge pricing_context_set_at + shipment_edit_intake_return heads

Revision ID: 636505b0c13a
Revises: d4f7e2a91c83, c3f9b1d4e7a2
Create Date: 2026-04-25 21:34:04.714829

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "636505b0c13a"
down_revision: Union[str, Sequence[str], None] = ("d4f7e2a91c83", "c3f9b1d4e7a2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
