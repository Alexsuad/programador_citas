"""Crea relacion recurso_servicio

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recurso_servicio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_recurso', sa.Integer(), nullable=False),
        sa.Column('id_servicio', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_recurso'], ['recursos.id_recurso']),
        sa.ForeignKeyConstraint(['id_servicio'], ['servicios.id_servicio']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurso_servicio_id'), 'recurso_servicio', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recurso_servicio_id'), table_name='recurso_servicio')
    op.drop_table('recurso_servicio')
