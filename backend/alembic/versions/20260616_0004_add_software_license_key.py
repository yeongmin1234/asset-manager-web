"""add software license key

Revision ID: 20260616_0004
Revises: 20260615_0003
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260616_0004"
down_revision = "20260615_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("software_items", sa.Column("license_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("software_items", "license_key")
