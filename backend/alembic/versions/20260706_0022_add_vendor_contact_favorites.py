"""add vendor contact favorites

Revision ID: 20260706_0022
Revises: 20260706_0021
Create Date: 2026-07-06 00:22:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260706_0022"
down_revision = "20260706_0021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vendor_contacts",
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade():
    op.drop_column("vendor_contacts", "is_favorite")
