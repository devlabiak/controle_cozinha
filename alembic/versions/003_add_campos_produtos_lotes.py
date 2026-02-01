"""Add campos de produto e lote

Revision ID: 003
Revises: 002
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alimentos
    op.add_column('alimentos', sa.Column('subcategoria', sa.String(length=120), nullable=True))
    op.add_column('alimentos', sa.Column('tipo_conservacao', sa.String(length=20), nullable=True))

    # Produto Lotes
    op.add_column('produto_lotes', sa.Column('quantidade_etiquetas', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('produto_lotes', sa.Column('fabricante', sa.String(length=255), nullable=True))
    op.add_column('produto_lotes', sa.Column('sif', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('produto_lotes', 'sif')
    op.drop_column('produto_lotes', 'fabricante')
    op.drop_column('produto_lotes', 'quantidade_etiquetas')
    op.drop_column('alimentos', 'tipo_conservacao')
    op.drop_column('alimentos', 'subcategoria')
