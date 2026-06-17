"""add activity log summary

Revision ID: 20260617_0008
Revises: 20260617_0007
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0008"
down_revision = "20260617_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_activity_logs", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("system_activity_logs", "summary")
