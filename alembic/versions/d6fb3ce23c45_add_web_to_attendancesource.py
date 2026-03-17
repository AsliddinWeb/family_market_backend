"""add_web_to_attendancesource

Revision ID: d6fb3ce23c45
Revises: cadfa323c6da
Create Date: 2026-03-17 18:50:30.342662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6fb3ce23c45'
down_revision: Union[str, None] = 'cadfa323c6da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE attendancesource ADD VALUE IF NOT EXISTS 'web'")


def downgrade() -> None:
    pass