"""Remove global email unique constraint and add per-client unique constraint

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
    # Remove constraint de UNIQUE global do email (permite mesmo email em clientes diferentes)
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    
    # Adicionar constraint UNIQUE composta (email + cliente_id)
    # Isso permite que um email seja usado em diferentes clientes, mas não dentro do mesmo cliente
    op.create_unique_constraint(
        'uq_users_email_cliente_id',
        'users',
        ['email', 'cliente_id'],
        postgresql_where=sa.text('cliente_id IS NOT NULL')
    )
    
    # Para usuários admin (cliente_id = NULL), garantir email único
    # Criar índice único para emails de admins
    op.create_unique_constraint(
        'uq_users_email_admin',
        'users',
        ['email'],
        postgresql_where=sa.text('cliente_id IS NULL')
    )


def downgrade() -> None:
    # Remover constraints compostas
    op.drop_constraint('uq_users_email_admin', 'users', type_='unique')
    op.drop_constraint('uq_users_email_cliente_id', 'users', type_='unique')
    
    # Restaurar constraint UNIQUE global
    op.create_unique_constraint(
        'users_email_key',
        'users',
        ['email']
    )
