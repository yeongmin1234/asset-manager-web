"""Record the reason category for recall application soft deletion.

Revision ID: 20260930_0048
Revises: 20260930_0047
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0048"
down_revision = "20260930_0047"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_applications", sa.Column("delete_reason_category", sa.String(40), nullable=True))


def downgrade():
    op.drop_column("recall_applications", "delete_reason_category")
