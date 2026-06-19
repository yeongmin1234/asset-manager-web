"""add beverage order type

Revision ID: 20260619_0015
Revises: 20260619_0014
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0015"
down_revision = "20260619_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "beverage_order_records",
        sa.Column("order_type", sa.String(length=20), nullable=False, server_default="beverage"),
    )
    op.create_index(
        op.f("ix_beverage_order_records_order_type"),
        "beverage_order_records",
        ["order_type"],
        unique=False,
    )
    op.alter_column("beverage_order_records", "order_type", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_beverage_order_records_order_type"), table_name="beverage_order_records")
    op.drop_column("beverage_order_records", "order_type")
