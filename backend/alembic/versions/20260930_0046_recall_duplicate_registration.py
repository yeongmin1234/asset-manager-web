"""Track repeated recall application Excel registrations.

Revision ID: 20260930_0046
Revises: 20260930_0045
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0046"
down_revision = "20260930_0045"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_applications", sa.Column("duplicate_registration_attempt", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("recall_applications", sa.Column("duplicate_registration_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("recall_applications", sa.Column("last_duplicate_registration_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_applications", sa.Column("last_duplicate_registration_batch_id", sa.Integer(), nullable=True))
    op.create_index("ix_recall_applications_duplicate_registration_attempt", "recall_applications", ["duplicate_registration_attempt"])
    op.create_foreign_key("fk_recall_application_last_duplicate_batch", "recall_applications",
                          "recall_application_upload_batches", ["last_duplicate_registration_batch_id"], ["id"], ondelete="SET NULL")


def downgrade():
    op.drop_constraint("fk_recall_application_last_duplicate_batch", "recall_applications", type_="foreignkey")
    op.drop_index("ix_recall_applications_duplicate_registration_attempt", table_name="recall_applications")
    op.drop_column("recall_applications", "last_duplicate_registration_batch_id")
    op.drop_column("recall_applications", "last_duplicate_registration_at")
    op.drop_column("recall_applications", "duplicate_registration_count")
    op.drop_column("recall_applications", "duplicate_registration_attempt")
