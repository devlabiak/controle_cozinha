"""Add role column to user_tenants_association

Revision ID: 005
Revises: 004
Create Date: 2026-02-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar coluna 'role' à tabela user_tenants_association
    # Usando VARCHAR em vez de ENUM para evitar conflitos com Python Enum
    op.add_column('user_tenants_association',
        sa.Column('role', sa.String(50), nullable=False, server_default='leitura')
    )


def downgrade() -> None:
    # Remover coluna 'role'
    op.drop_column('user_tenants_association', 'role')
