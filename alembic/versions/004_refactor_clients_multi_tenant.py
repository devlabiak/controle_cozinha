"""Refactor: Add Cliente table and multi-tenant user relationship

Revision ID: 004
Revises: 003
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create clientes table
    op.create_table(
        'clientes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome_empresa', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('cnpj', sa.String(20), nullable=True, unique=True),
        sa.Column('endereco', sa.String(255), nullable=True),
        sa.Column('cidade', sa.String(100), nullable=True),
        sa.Column('estado', sa.String(2), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('cnpj'),
    )
    op.create_index('ix_clientes_id', 'clientes', ['id'])
    op.create_index('ix_clientes_email', 'clientes', ['email'])

    # Add cliente_id to tenants
    op.add_column('tenants', sa.Column('cliente_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_tenants_cliente_id', 'tenants', 'clientes', ['cliente_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_tenants_cliente_id', 'tenants', ['cliente_id'])

    # Create user_tenants_association table (many-to-many)
    op.create_table(
        'user_tenants_association',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'tenant_id')
    )

    # Modify users table
    op.add_column('users', sa.Column('cliente_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_cliente_id', 'users', 'clientes', ['cliente_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_users_cliente_id', 'users', ['cliente_id'])
    
    # Drop old tenant_id column from users
    # Using execute for raw SQL to handle constraint name variations
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_tenant_id')
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_fkey')
    
    op.drop_column('users', 'tenant_id')
    op.drop_column('users', 'is_tenant_admin')

    # Add audit columns to alimentos
    op.add_column('alimentos', sa.Column('created_by', sa.Integer(), nullable=True))
    op.add_column('alimentos', sa.Column('updated_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_alimentos_created_by', 'alimentos', 'users', ['created_by'], ['id'])
    op.create_foreign_key('fk_alimentos_updated_by', 'alimentos', 'users', ['updated_by'], ['id'])


def downgrade() -> None:
    # Drop audit columns from alimentos
    op.drop_constraint('fk_alimentos_updated_by', 'alimentos', type_='foreignkey')
    op.drop_constraint('fk_alimentos_created_by', 'alimentos', type_='foreignkey')
    op.drop_column('alimentos', 'updated_by')
    op.drop_column('alimentos', 'created_by')

    # Restore users table
    op.add_column('users', sa.Column('is_tenant_admin', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    op.drop_index('ix_users_cliente_id', 'users')
    op.drop_constraint('fk_users_cliente_id', 'users', type_='foreignkey')
    op.drop_column('users', 'cliente_id')

    # Drop user_tenants_association
    op.drop_table('user_tenants_association')

    # Remove cliente from tenants
    op.drop_index('ix_tenants_cliente_id', 'tenants')
    op.drop_constraint('fk_tenants_cliente_id', 'tenants', type_='foreignkey')
    op.drop_column('tenants', 'cliente_id')

    # Drop clientes table
    op.drop_index('ix_clientes_email', 'clientes')
    op.drop_index('ix_clientes_id', 'clientes')
    op.drop_table('clientes')
