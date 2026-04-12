"""Agrega perfil_servicio a servicios

Revision ID: b31f4c8d9a10
Revises: 05a87794d4cc
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b31f4c8d9a10'
down_revision: Union[str, Sequence[str], None] = '05a87794d4cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'servicios',
        sa.Column('perfil_servicio', sa.String(length=20), nullable=False, server_default='unisex')
    )


def downgrade() -> None:
    op.drop_column('servicios', 'perfil_servicio')
