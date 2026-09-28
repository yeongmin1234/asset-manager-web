"""create recall application upload, application, and status history tables

Revision ID: 20260928_0038
Revises: 20260715_0037
"""
from alembic import op
import sqlalchemy as sa


revision = "20260928_0038"
down_revision = "20260715_0037"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recall_application_upload_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("excluded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_recall_application_upload_batches_source_sha256", "recall_application_upload_batches", ["source_sha256"], unique=True)
    op.create_index("ix_recall_application_upload_batches_uploaded_by", "recall_application_upload_batches", ["uploaded_by"])

    op.create_table(
        "recall_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("upload_batch_id", sa.Integer(), sa.ForeignKey("recall_application_upload_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(100), nullable=False),
        sa.Column("phone_original", sa.String(50), nullable=False),
        sa.Column("phone_normalized", sa.String(20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("pickup_agreement", sa.String(100), nullable=True),
        sa.Column("pickup_date", sa.Date(), nullable=True),
        sa.Column("replacement_shipping_agreement", sa.String(100), nullable=True),
        sa.Column("current_status", sa.String(40), nullable=False, server_default="APPLICATION_RECEIVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("upload_batch_id", "source_row_number", name="uq_recall_application_batch_row"),
    )
    for column in ("upload_batch_id", "customer_name", "phone_normalized", "serial_number", "current_status", "created_at", "created_by"):
        op.create_index("ix_recall_applications_{}".format(column), "recall_applications", [column])

    op.create_table(
        "recall_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recall_application_id", sa.Integer(), sa.ForeignKey("recall_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(40), nullable=True),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("change_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
    )
    for column in ("recall_application_id", "new_status", "changed_by"):
        op.create_index("ix_recall_status_history_{}".format(column), "recall_status_history", [column])


def downgrade():
    op.drop_table("recall_status_history")
    op.drop_table("recall_applications")
    op.drop_table("recall_application_upload_batches")
