"""add asset spec image path

Revision ID: 20260622_0016
Revises: 20260619_0015
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260622_0016"
down_revision = "20260619_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("spec_image_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "spec_image_path")
