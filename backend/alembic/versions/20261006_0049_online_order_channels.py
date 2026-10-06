"""Create editable online order channels.

Revision ID: 20261006_0049
Revises: 20260930_0048
"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0049"
down_revision = "20260930_0048"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "online_order_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.CheckConstraint("NOT is_default OR is_active", name="ck_online_order_channels_default_active"),
    )
    op.create_index("ix_online_order_channels_code", "online_order_channels", ["code"], unique=True)
    op.create_index(
        "ux_online_order_channels_one_default", "online_order_channels", ["is_default"],
        unique=True, postgresql_where=sa.text("is_default"), sqlite_where=sa.text("is_default"),
    )
    op.bulk_insert(
        sa.table(
            "online_order_channels",
            sa.column("name", sa.String()), sa.column("code", sa.String()),
            sa.column("description", sa.Text()), sa.column("is_active", sa.Boolean()),
            sa.column("is_default", sa.Boolean()),
        ),
        [{"name": "스마트스토어", "code": "smartstore", "description": "네이버 스마트스토어", "is_active": True, "is_default": True}],
    )


def downgrade():
    op.drop_index("ux_online_order_channels_one_default", table_name="online_order_channels")
    op.drop_index("ix_online_order_channels_code", table_name="online_order_channels")
    op.drop_table("online_order_channels")
