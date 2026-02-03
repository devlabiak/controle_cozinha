"""add composite indexes for performance

Revision ID: 007
Revises: 006
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def index_exists(index_name):
    """Verifica se um índice já existe no banco de dados."""
    connection = op.get_bind()
    result = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :index_name)"
        ),
        {"index_name": index_name}
    )
    return result.scalar()


def upgrade():
    """Adiciona índices compostos para queries comuns e melhoria de performance."""
    
    # Índices para movimentacoes_estoque - queries por tenant + tipo + data
    if not index_exists('ix_movimentacoes_tenant_tipo'):
        op.create_index(
            'ix_movimentacoes_tenant_tipo', 
            'movimentacoes_estoque', 
            ['tenant_id', 'tipo'],
            unique=False
        )
    
    if not index_exists('ix_movimentacoes_tenant_validade'):
        op.create_index(
            'ix_movimentacoes_tenant_validade', 
            'movimentacoes_estoque', 
            ['tenant_id', 'data_validade'],
            unique=False
        )
    
    if not index_exists('ix_movimentacoes_tenant_qrcode'):
        op.create_index(
            'ix_movimentacoes_tenant_qrcode', 
            'movimentacoes_estoque', 
            ['tenant_id', 'qr_code_usado'],
            unique=False
        )
    
    # Índices para produto_lotes - queries por tenant + status
    if not index_exists('ix_lotes_tenant_ativo_usado'):
        op.create_index(
            'ix_lotes_tenant_ativo_usado', 
            'produto_lotes', 
            ['tenant_id', 'ativo', 'usado_completamente'],
            unique=False
        )
    
    if not index_exists('ix_lotes_tenant_validade'):
        op.create_index(
            'ix_lotes_tenant_validade', 
            'produto_lotes', 
            ['tenant_id', 'data_validade'],
            unique=False
        )
    
    # Índices para alimentos - queries por tenant + categoria
    if not index_exists('ix_alimentos_tenant_categoria'):
        op.create_index(
            'ix_alimentos_tenant_categoria', 
            'alimentos', 
            ['tenant_id', 'categoria'],
            unique=False
        )
    
    if not index_exists('ix_alimentos_tenant_ativo'):
        op.create_index(
            'ix_alimentos_tenant_ativo', 
            'alimentos', 
            ['tenant_id', 'ativo'],
            unique=False
        )
    
    # Índice para print_jobs - queries por tenant + status
    if not index_exists('ix_printjobs_tenant_status'):
        op.create_index(
            'ix_printjobs_tenant_status', 
            'print_jobs', 
            ['tenant_id', 'status'],
            unique=False
        )
    
    # Índice para audit_logs - queries por tenant + timestamp
    if not index_exists('ix_auditlogs_tenant_timestamp'):
        op.create_index(
            'ix_auditlogs_tenant_timestamp', 
            'audit_logs', 
            ['tenant_id', 'timestamp'],
            unique=False
        )


def downgrade():
    """Remove os índices compostos."""
    
    op.drop_index('ix_auditlogs_tenant_timestamp', table_name='audit_logs')
    op.drop_index('ix_printjobs_tenant_status', table_name='print_jobs')
    op.drop_index('ix_alimentos_tenant_ativo', table_name='alimentos')
    op.drop_index('ix_alimentos_tenant_categoria', table_name='alimentos')
    op.drop_index('ix_lotes_tenant_validade', table_name='produto_lotes')
    op.drop_index('ix_lotes_tenant_ativo_usado', table_name='produto_lotes')
    op.drop_index('ix_movimentacoes_tenant_qrcode', table_name='movimentacoes_estoque')
    op.drop_index('ix_movimentacoes_tenant_validade', table_name='movimentacoes_estoque')
    op.drop_index('ix_movimentacoes_tenant_tipo', table_name='movimentacoes_estoque')
