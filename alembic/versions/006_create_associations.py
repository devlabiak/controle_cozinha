"""Consolidate multi-tenant structure and associations

Revision ID: 006
Revises: 005
Create Date: 2026-02-01 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela user_tenants_association (many-to-many entre users e tenants)
    op.create_table(
        'user_tenants_association',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='leitura'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'tenant_id')
    )

    # Criar tabela user_clientes_association (many-to-many entre users e clientes)
    op.create_table(
        'user_clientes_association',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'cliente_id')
    )


def downgrade() -> None:
    op.drop_table('user_clientes_association')
    op.drop_table('user_tenants_association')
