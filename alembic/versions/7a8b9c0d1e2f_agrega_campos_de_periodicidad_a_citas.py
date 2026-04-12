"""Agrega campos de periodicidad a citas

Revision ID: 7a8b9c0d1e2f
Revises: e5d6c7b8a901
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = 'e5d6c7b8a901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('citas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dias_recordatorio_reagendamiento', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('fecha_recordatorio_reagendamiento', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('recordatorio_reagendamiento_enviado', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('citas', schema=None) as batch_op:
        batch_op.drop_column('recordatorio_reagendamiento_enviado')
        batch_op.drop_column('fecha_recordatorio_reagendamiento')
        batch_op.drop_column('dias_recordatorio_reagendamiento')
