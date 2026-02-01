"""Add usuario_clientes association table for multi-company access

Revision ID: 007
Revises: 006
Create Date: 2026-02-01 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the user_clientes_association table
    # This allows users to have access to multiple companies
    op.create_table(
        'user_clientes_association',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'cliente_id')
    )
    
    # Create index for performance
    op.create_index('ix_user_clientes_user_id', 'user_clientes_association', ['user_id'])
    op.create_index('ix_user_clientes_cliente_id', 'user_clientes_association', ['cliente_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_clientes_cliente_id', 'user_clientes_association')
    op.drop_index('ix_user_clientes_user_id', 'user_clientes_association')
    
    # Drop the table
    op.drop_table('user_clientes_association')
