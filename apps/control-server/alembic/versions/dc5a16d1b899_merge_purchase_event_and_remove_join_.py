"""merge_purchase_event_and_remove_join_code

Revision ID: dc5a16d1b899
Revises: 0019_purchase_event, c4a23ddc0287
Create Date: 2026-03-04 02:53:20.487870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc5a16d1b899'
down_revision: Union[str, None] = ('0019_purchase_event', 'c4a23ddc0287')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
