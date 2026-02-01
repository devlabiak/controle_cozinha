"""Add missing columns to tenants table

Revision ID: 006
Revises: 005
Create Date: 2026-02-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to tenants table only if they don't exist
    op.execute('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS cnpj VARCHAR(20)')
    op.execute('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS endereco VARCHAR(255)')


def downgrade() -> None:
    # Remove added columns
    op.drop_column('tenants', 'endereco')
    op.drop_column('tenants', 'cnpj')
