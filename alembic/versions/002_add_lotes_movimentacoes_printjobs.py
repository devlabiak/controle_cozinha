"""Add lotes, movimentacoes and print_jobs tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela produto_lotes
    op.create_table(
        'produto_lotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('alimento_id', sa.Integer(), nullable=False),
        sa.Column('lote_numero', sa.String(length=50), nullable=False),
        sa.Column('qr_code', sa.String(length=100), nullable=False),
        sa.Column('data_fabricacao', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_validade', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quantidade_produzida', sa.Float(), nullable=False),
        sa.Column('quantidade_disponivel', sa.Float(), nullable=False),
        sa.Column('unidade_medida', sa.String(length=20), nullable=True),
        sa.Column('peso_liquido', sa.String(length=50), nullable=True),
        sa.Column('ingredientes', sa.Text(), nullable=True),
        sa.Column('informacao_nutricional', sa.Text(), nullable=True),
        sa.Column('modo_conservacao', sa.Text(), nullable=True),
        sa.Column('responsavel_tecnico', sa.String(length=255), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True, default=True),
        sa.Column('usado_completamente', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alimento_id'], ['alimentos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_produto_lotes_id'), 'produto_lotes', ['id'], unique=False)
    op.create_index(op.f('ix_produto_lotes_tenant_id'), 'produto_lotes', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_produto_lotes_alimento_id'), 'produto_lotes', ['alimento_id'], unique=False)
    op.create_index(op.f('ix_produto_lotes_lote_numero'), 'produto_lotes', ['lote_numero'], unique=False)
    op.create_index(op.f('ix_produto_lotes_qr_code'), 'produto_lotes', ['qr_code'], unique=True)

    # Criar tabela movimentacoes_estoque
    op.create_table(
        'movimentacoes_estoque',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('alimento_id', sa.Integer(), nullable=False),
        sa.Column('lote_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('entrada', 'saida', 'ajuste', 'uso', name='tipomovimentacao'), nullable=False),
        sa.Column('quantidade', sa.Float(), nullable=False),
        sa.Column('quantidade_anterior', sa.Float(), nullable=True),
        sa.Column('quantidade_nova', sa.Float(), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('qr_code_usado', sa.String(length=100), nullable=True),
        sa.Column('localizacao', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alimento_id'], ['alimentos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lote_id'], ['produto_lotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_movimentacoes_estoque_id'), 'movimentacoes_estoque', ['id'], unique=False)
    op.create_index(op.f('ix_movimentacoes_estoque_tenant_id'), 'movimentacoes_estoque', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_movimentacoes_estoque_alimento_id'), 'movimentacoes_estoque', ['alimento_id'], unique=False)
    op.create_index(op.f('ix_movimentacoes_estoque_lote_id'), 'movimentacoes_estoque', ['lote_id'], unique=False)
    op.create_index(op.f('ix_movimentacoes_estoque_tipo'), 'movimentacoes_estoque', ['tipo'], unique=False)
    op.create_index(op.f('ix_movimentacoes_estoque_created_at'), 'movimentacoes_estoque', ['created_at'], unique=False)

    # Criar tabela print_jobs
    op.create_table(
        'print_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('lote_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'printing', 'completed', 'failed', name='statusprintjob'), nullable=True, default='pending'),
        sa.Column('tentativas', sa.Integer(), nullable=True, default=0),
        sa.Column('erro_mensagem', sa.Text(), nullable=True),
        sa.Column('etiqueta_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('printed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lote_id'], ['produto_lotes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_print_jobs_id'), 'print_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_print_jobs_tenant_id'), 'print_jobs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_print_jobs_status'), 'print_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_print_jobs_created_at'), 'print_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_print_jobs_created_at'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_status'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_tenant_id'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_id'), table_name='print_jobs')
    op.drop_table('print_jobs')
    
    op.drop_index(op.f('ix_movimentacoes_estoque_created_at'), table_name='movimentacoes_estoque')
    op.drop_index(op.f('ix_movimentacoes_estoque_tipo'), table_name='movimentacoes_estoque')
    op.drop_index(op.f('ix_movimentacoes_estoque_lote_id'), table_name='movimentacoes_estoque')
    op.drop_index(op.f('ix_movimentacoes_estoque_alimento_id'), table_name='movimentacoes_estoque')
    op.drop_index(op.f('ix_movimentacoes_estoque_tenant_id'), table_name='movimentacoes_estoque')
    op.drop_index(op.f('ix_movimentacoes_estoque_id'), table_name='movimentacoes_estoque')
    op.drop_table('movimentacoes_estoque')
    
    op.drop_index(op.f('ix_produto_lotes_qr_code'), table_name='produto_lotes')
    op.drop_index(op.f('ix_produto_lotes_lote_numero'), table_name='produto_lotes')
    op.drop_index(op.f('ix_produto_lotes_alimento_id'), table_name='produto_lotes')
    op.drop_index(op.f('ix_produto_lotes_tenant_id'), table_name='produto_lotes')
    op.drop_index(op.f('ix_produto_lotes_id'), table_name='produto_lotes')
    op.drop_table('produto_lotes')
