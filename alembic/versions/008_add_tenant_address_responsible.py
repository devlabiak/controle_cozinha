"""add tenant address and responsible fields

Revision ID: 008
Revises: 007
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Verifica se uma coluna já existe na tabela."""
    connection = op.get_bind()
    result = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name}
    )
    return result.scalar()


def upgrade():
    """Adiciona campos detalhados de endereço e pessoa responsável na tabela tenants."""
    
    # Adicionar campos de endereço detalhado
    if not column_exists('tenants', 'rua'):
        op.add_column('tenants', sa.Column('rua', sa.String(length=255), nullable=True))
    if not column_exists('tenants', 'numero'):
        op.add_column('tenants', sa.Column('numero', sa.String(length=20), nullable=True))
    if not column_exists('tenants', 'complemento'):
        op.add_column('tenants', sa.Column('complemento', sa.String(length=100), nullable=True))
    if not column_exists('tenants', 'bairro'):
        op.add_column('tenants', sa.Column('bairro', sa.String(length=100), nullable=True))
    if not column_exists('tenants', 'cidade'):
        op.add_column('tenants', sa.Column('cidade', sa.String(length=100), nullable=True))
    if not column_exists('tenants', 'estado'):
        op.add_column('tenants', sa.Column('estado', sa.String(length=2), nullable=True))
    if not column_exists('tenants', 'cep'):
        op.add_column('tenants', sa.Column('cep', sa.String(length=10), nullable=True))
    
    # Adicionar campos de pessoa responsável
    if not column_exists('tenants', 'responsavel_nome'):
        op.add_column('tenants', sa.Column('responsavel_nome', sa.String(length=255), nullable=True))
    if not column_exists('tenants', 'responsavel_telefone'):
        op.add_column('tenants', sa.Column('responsavel_telefone', sa.String(length=20), nullable=True))
    if not column_exists('tenants', 'responsavel_email'):
        op.add_column('tenants', sa.Column('responsavel_email', sa.String(length=255), nullable=True))
    if not column_exists('tenants', 'responsavel_cargo'):
        op.add_column('tenants', sa.Column('responsavel_cargo', sa.String(length=100), nullable=True))


def downgrade():
    """Remove os campos adicionados."""
    
    # Remover campos de pessoa responsável
    op.drop_column('tenants', 'responsavel_cargo')
    op.drop_column('tenants', 'responsavel_email')
    op.drop_column('tenants', 'responsavel_telefone')
    op.drop_column('tenants', 'responsavel_nome')
    
    # Remover campos de endereço detalhado
    op.drop_column('tenants', 'cep')
    op.drop_column('tenants', 'estado')
    op.drop_column('tenants', 'cidade')
    op.drop_column('tenants', 'bairro')
    op.drop_column('tenants', 'complemento')
    op.drop_column('tenants', 'numero')
    op.drop_column('tenants', 'rua')
