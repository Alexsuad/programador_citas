"""Agrega calificacion de servicio a citas

Revision ID: e5d6c7b8a901
Revises: b31f4c8d9a10
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5d6c7b8a901'
down_revision: Union[str, Sequence[str], None] = 'b31f4c8d9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos columnas con batch_alter_table para compatibilidad con SQLite
    with op.batch_alter_table('citas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calificacion_servicio', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('fecha_calificacion', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('citas', schema=None) as batch_op:
        batch_op.drop_column('fecha_calificacion')
        batch_op.drop_column('calificacion_servicio')
