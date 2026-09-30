"""Allow a deleted recall application to be reimported from the same Excel file.

Revision ID: 20260930_0047
Revises: 20260930_0046
"""

from alembic import op


revision = "20260930_0047"
down_revision = "20260930_0046"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_recall_application_upload_batches_source_sha256",
                  table_name="recall_application_upload_batches")
    op.create_index("ix_recall_application_upload_batches_source_sha256",
                    "recall_application_upload_batches", ["source_sha256"])


def downgrade():
    op.drop_index("ix_recall_application_upload_batches_source_sha256",
                  table_name="recall_application_upload_batches")
    op.create_index("ix_recall_application_upload_batches_source_sha256",
                    "recall_application_upload_batches", ["source_sha256"], unique=True)
