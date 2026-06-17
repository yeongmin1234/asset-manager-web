"""add asset location fields

Revision ID: 20260617_0010
Revises: 20260617_0009
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0010"
down_revision = "20260617_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("location_group", sa.String(length=50), nullable=True))
    op.add_column("assets", sa.Column("location_detail", sa.String(length=150), nullable=True))
    op.create_index("ix_assets_location_group", "assets", ["location_group"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_location_group", table_name="assets")
    op.drop_column("assets", "location_detail")
    op.drop_column("assets", "location_group")
