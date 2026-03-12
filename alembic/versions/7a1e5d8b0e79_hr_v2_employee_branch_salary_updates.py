"""hr_v2_employee_branch_salary_updates

Revision ID: 7a1e5d8b0e79
Revises: cae22595e72a
Create Date: 2026-03-11 12:10:06.549009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7a1e5d8b0e79'
down_revision: Union[str, None] = 'cae22595e72a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bonuses', sa.Column('auto_generated', sa.Boolean(), nullable=False, server_default='false', comment="True bo'lsa — tizim tomonidan avtomatik yaratilgan"))
    op.add_column('bonuses', sa.Column('attendance_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'bonuses', 'attendance', ['attendance_id'], ['id'])
    op.add_column('branches', sa.Column('work_end_time', sa.Time(), nullable=False, server_default='18:00:00'))
    op.add_column('branches', sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('branches', sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('branches', sa.Column('radius_meters', sa.Integer(), nullable=False, server_default='200'))
    op.add_column('employees', sa.Column('hourly_rate', sa.Numeric(precision=15, scale=2), nullable=True, comment="Soatlik stavka. Agar None bo'lsa base_salary/work_hours_per_day/22 dan hisoblanadi"))
    op.add_column('employees', sa.Column('work_hours_per_day', sa.Integer(), nullable=False, server_default='8', comment='Kunlik ish soati (default 8)'))
    op.add_column('employees', sa.Column('off_days', sa.JSON(), nullable=False, server_default='["saturday", "sunday"]', comment="Dam olish kunlari: ['saturday', 'sunday']"))
    op.add_column('employees', sa.Column('face_photo', sa.String(length=255), nullable=True, comment="Yuz tanish uchun referans rasm yo'li"))
    op.alter_column('employees', 'photo',
               existing_type=sa.VARCHAR(length=255),
               comment="Profil rasmi yo'li",
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('employees', 'photo',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment="Profil rasmi yo'li",
               existing_nullable=True)
    op.drop_column('employees', 'face_photo')
    op.drop_column('employees', 'off_days')
    op.drop_column('employees', 'work_hours_per_day')
    op.drop_column('employees', 'hourly_rate')
    op.drop_column('branches', 'radius_meters')
    op.drop_column('branches', 'longitude')
    op.drop_column('branches', 'latitude')
    op.drop_column('branches', 'work_end_time')
    op.drop_constraint(None, 'bonuses', type_='foreignkey')
    op.drop_column('bonuses', 'attendance_id')
    op.drop_column('bonuses', 'auto_generated')