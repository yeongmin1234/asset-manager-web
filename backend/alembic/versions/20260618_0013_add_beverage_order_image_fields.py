"""add beverage order image fields

Revision ID: 20260618_0013
Revises: 20260618_0012
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0013"
down_revision = "20260618_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "beverage_order_records",
        sa.Column("image_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "beverage_order_records",
        sa.Column("image_original_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("beverage_order_records", "image_original_name")
    op.drop_column("beverage_order_records", "image_path")
