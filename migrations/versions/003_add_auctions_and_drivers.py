"""add auctions and drivers tables

Revision ID: 003
Revises: 002
Create Date: 2025-05-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'auctions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('start_price', sa.Integer(), nullable=False),
        sa.Column('reserve_price', sa.Integer(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'active', 'ended', 'cancelled', name='auctionstatus'), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('winner_user_id', sa.Integer(), nullable=True),
        sa.Column('winning_bid_amount', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id']),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.ForeignKeyConstraint(['winner_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('reserve_price <= start_price', name='ck_auction_reserve'),
    )
    op.create_index('ix_auction_listing', 'auctions', ['listing_id'])
    op.create_index('ix_auction_status_ends', 'auctions', ['status', 'ends_at'])

    op.create_table(
        'auction_bids',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('auction_id', sa.Integer(), nullable=False),
        sa.Column('bidder_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['bidder_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('amount >= 0', name='ck_bid_amount_nonneg'),
    )
    op.create_index('ix_bid_auction_amount', 'auction_bids', ['auction_id', 'amount'])

    op.create_table(
        'drivers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_type', sa.Enum('bicycle', 'scooter', 'car', 'walk', name='vehicletype'), nullable=False, server_default=sa.text("'bicycle'")),
        sa.Column('current_lat', sa.Float(), nullable=True),
        sa.Column('current_lng', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('available', 'busy', 'offline', name='driverstatus'), nullable=False, server_default=sa.text("'offline'")),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('rating', sa.Float(), nullable=False, server_default=sa.text('5.0')),
        sa.Column('total_deliveries', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_driver_user', 'drivers', ['user_id'])

    op.create_table(
        'deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('pickup_lat', sa.Float(), nullable=False),
        sa.Column('pickup_lng', sa.Float(), nullable=False),
        sa.Column('delivery_lat', sa.Float(), nullable=False),
        sa.Column('delivery_lng', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('assigned', 'en_route_pickup', 'at_pickup', 'en_route_delivery', 'delivered', 'failed', name='deliverystatus'), nullable=False, server_default=sa.text("'assigned'")),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('picked_up_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
    )
    op.create_index('ix_delivery_driver_status', 'deliveries', ['driver_id', 'status'])
    op.create_index('ix_delivery_order', 'deliveries', ['order_id'])


def downgrade() -> None:
    op.drop_table('deliveries')
    op.drop_table('drivers')
    op.drop_table('auction_bids')
    op.drop_table('auctions')
    op.execute('DROP TYPE IF EXISTS deliverystatus')
    op.execute('DROP TYPE IF EXISTS driverstatus')
    op.execute('DROP TYPE IF EXISTS vehicletype')
    op.execute('DROP TYPE IF EXISTS auctionstatus')
