"""add user phone

Revision ID: 3f4b9c1d2e5a
Revises: 139f3b8072e0
Create Date: 2026-05-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '3f4b9c1d2e5a'
down_revision = '139f3b8072e0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('phone')
