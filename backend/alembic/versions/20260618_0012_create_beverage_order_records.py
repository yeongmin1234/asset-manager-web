"""create beverage order records

Revision ID: 20260618_0012
Revises: 20260618_0011
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0012"
down_revision = "20260618_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beverage_order_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("order_month", sa.String(length=7), nullable=True),
        sa.Column("vendor", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("items_summary", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 0), nullable=True),
        sa.Column("quantity_summary", sa.Text(), nullable=True),
        sa.Column("requester", sa.String(length=100), nullable=True),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("order_url", sa.Text(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_beverage_order_records_id"),
        "beverage_order_records",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beverage_order_records_order_date"),
        "beverage_order_records",
        ["order_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beverage_order_records_order_month"),
        "beverage_order_records",
        ["order_month"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beverage_order_records_vendor"),
        "beverage_order_records",
        ["vendor"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beverage_order_records_title"),
        "beverage_order_records",
        ["title"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beverage_order_records_requester"),
        "beverage_order_records",
        ["requester"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_beverage_order_records_requester"),
        table_name="beverage_order_records",
    )
    op.drop_index(
        op.f("ix_beverage_order_records_title"),
        table_name="beverage_order_records",
    )
    op.drop_index(
        op.f("ix_beverage_order_records_vendor"),
        table_name="beverage_order_records",
    )
    op.drop_index(
        op.f("ix_beverage_order_records_order_month"),
        table_name="beverage_order_records",
    )
    op.drop_index(
        op.f("ix_beverage_order_records_order_date"),
        table_name="beverage_order_records",
    )
    op.drop_index(
        op.f("ix_beverage_order_records_id"),
        table_name="beverage_order_records",
    )
    op.drop_table("beverage_order_records")
