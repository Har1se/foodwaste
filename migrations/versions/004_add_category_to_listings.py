"""add category column to listings

Revision ID: 004
Revises: 003
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('category', sa.String(length=50), nullable=True))
    op.create_index('ix_listings_category', 'listings', ['category'])


def downgrade() -> None:
    op.drop_index('ix_listings_category', table_name='listings')
    op.drop_column('listings', 'category')
