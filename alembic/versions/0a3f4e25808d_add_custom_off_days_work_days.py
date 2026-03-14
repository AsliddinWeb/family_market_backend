"""add_custom_off_days_work_days

Revision ID: 0a3f4e25808d
Revises: caae22fa19b8
Create Date: 2026-03-14 13:15:28.807809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0a3f4e25808d'
down_revision: Union[str, None] = 'caae22fa19b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Nullable bilan qo'shamiz (mavjud qatorlar uchun)
    op.add_column('employees', sa.Column(
        'custom_off_days', sa.JSON(), nullable=True,
        comment="Qo'shimcha dam olish kunlari (aniq sana): ['2026-03-08', '2026-03-15']"
    ))
    op.add_column('employees', sa.Column(
        'custom_work_days', sa.JSON(), nullable=True,
        comment="Odatda dam olish kuni bo'lsa ham ishlagan kunlar: ['2026-03-01']"
    ))

    # 2. Mavjud NULL qatorlarga default [] beramiz
    op.execute("UPDATE employees SET custom_off_days = '[]' WHERE custom_off_days IS NULL")
    op.execute("UPDATE employees SET custom_work_days = '[]' WHERE custom_work_days IS NULL")

    # 3. Endi NOT NULL qilamiz
    op.alter_column('employees', 'custom_off_days',  nullable=False)
    op.alter_column('employees', 'custom_work_days', nullable=False)

    # 4. off_days comment yangilash
    op.alter_column('employees', 'off_days',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="Haftalik dam olish kunlari: ['saturday', 'sunday']",
        existing_comment="Dam olish kunlari: ['saturday', 'sunday']",
        existing_nullable=False,
        existing_server_default=sa.text('\'["saturday", "sunday"]\'::json')
    )


def downgrade() -> None:
    op.alter_column('employees', 'off_days',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="Dam olish kunlari: ['saturday', 'sunday']",
        existing_comment="Haftalik dam olish kunlari: ['saturday', 'sunday']",
        existing_nullable=False,
        existing_server_default=sa.text('\'["saturday", "sunday"]\'::json')
    )
    op.drop_column('employees', 'custom_work_days')
    op.drop_column('employees', 'custom_off_days')