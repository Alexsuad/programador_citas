"""Agrega perfil_recurso a recursos

Revision ID: a1b2c3d4e5f6
Revises: 7a8b9c0d1e2f
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recursos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('perfil_recurso', sa.String(length=20), nullable=False, server_default='unisex')
        )


def downgrade() -> None:
    with op.batch_alter_table('recursos', schema=None) as batch_op:
        batch_op.drop_column('perfil_recurso')
