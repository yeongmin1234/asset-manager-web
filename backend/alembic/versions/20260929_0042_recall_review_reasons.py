"""Store coded reasons for recall applications requiring review.

Revision ID: 20260929_0042
Revises: 20260929_0041
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0042"
down_revision = "20260929_0041"
branch_labels = None
depends_on = None


def upgrade():
    # NULL marks historical rows; their reasons are derived from existing fields on read.
    op.add_column("recall_applications", sa.Column("review_reason_codes", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("recall_applications", "review_reason_codes")
