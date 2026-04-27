"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('customer', 'vendor', 'driver', 'admin', name='userrole'),
                  nullable=False, server_default='customer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('allergen_profile', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)

    # ── otp_codes ─────────────────────────────────────────────────────────────
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_codes_user_id', 'otp_codes', ['user_id'])

    # ── vendors ───────────────────────────────────────────────────────────────
    op.create_table(
        'vendors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('business_name', sa.String(length=255), nullable=False),
        sa.Column('bin_number', sa.String(length=12), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('platform_fee_pct', sa.Float(), nullable=False, server_default='15.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bin_number'),
    )
    op.create_index('ix_vendors_user_id', 'vendors', ['user_id'], unique=True)

    # ── listings ──────────────────────────────────────────────────────────────
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=False),
        sa.Column('original_price', sa.Integer(), nullable=False),
        sa.Column('current_price', sa.Integer(), nullable=False),
        sa.Column('discount_percentage', sa.Float(), nullable=False),
        sa.Column('quantity_total', sa.Integer(), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=False),
        sa.Column('status',
                  sa.Enum('draft', 'active', 'discounted', 'free', 'compost',
                          'paused', 'sold_out', name='listingstatus'),
                  nullable=False, server_default='draft'),
        sa.Column('pickup_window_start', sa.DateTime(), nullable=False),
        sa.Column('pickup_window_end', sa.DateTime(), nullable=False),
        sa.Column('days_active', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint('current_price <= original_price', name='ck_price_order'),
        sa.CheckConstraint('current_price >= 0', name='ck_floor_price'),
        sa.CheckConstraint('quantity_available >= 0', name='ck_qty_nonneg'),
        sa.CheckConstraint('discount_percentage BETWEEN 1 AND 90', name='ck_discount'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_listing_vendor_status', 'listings', ['vendor_id', 'status'])
    op.create_index('ix_listing_geo', 'listings', ['latitude', 'longitude'])
    op.create_index('ix_listings_vendor_id', 'listings', ['vendor_id'])

    # ── listing_allergens ─────────────────────────────────────────────────────
    op.create_table(
        'listing_allergens',
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('allergen_code', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id']),
        sa.PrimaryKeyConstraint('listing_id', 'allergen_code'),
    )

    # ── orders ────────────────────────────────────────────────────────────────
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('status',
                  sa.Enum('pending', 'confirmed', 'ready_for_pickup',
                          'picked_up', 'cancelled', 'expired', name='orderstatus'),
                  nullable=False, server_default='pending'),
        sa.Column('total_amount', sa.Integer(), nullable=False),
        sa.Column('pickup_token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pickup_token'),
    )
    op.create_index('ix_order_customer', 'orders', ['customer_id', 'status'])
    op.create_index('ix_order_vendor', 'orders', ['vendor_id', 'status'])

    # ── order_items ───────────────────────────────────────────────────────────
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('amount_kzt', sa.Integer(), nullable=False),
        sa.Column('status',
                  sa.Enum('pending', 'completed', 'failed', 'refunded',
                          name='paymentstatus'),
                  nullable=False, server_default='pending'),
        sa.Column('kaspi_ref_id', sa.String(length=100), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
        sa.UniqueConstraint('kaspi_ref_id'),
    )

    # ── audit_logs (append-only) ──────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('old_data', sa.Text(), nullable=True),
        sa.Column('new_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_actor_time', 'audit_logs', ['actor_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('payments')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('listing_allergens')
    op.drop_table('listings')
    op.drop_table('vendors')
    op.drop_table('otp_codes')
    op.drop_table('users')

    # Drop enums (PostgreSQL specific)
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS listingstatus")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
