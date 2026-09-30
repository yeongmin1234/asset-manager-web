"""Add cumulative raw recall targets.

Revision ID: 20260930_0043
Revises: 20260929_0042
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0043"
down_revision = "20260929_0042"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recall_target_upload_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("normal_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_table(
        "recall_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("recall_target_upload_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("sales_channel", sa.String(100)),
        sa.Column("original_order_no", sa.String(100)),
        sa.Column("customer_name", sa.String(100)),
        sa.Column("phone_raw", sa.String(100)),
        sa.Column("phone_normalized", sa.String(30)),
        sa.Column("address", sa.Text()),
        sa.Column("delivery_message", sa.Text()),
        sa.Column("serial_number", sa.String(100)),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("purchase_date", sa.Date()),
        sa.Column("duplicate_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duplicate_reason", sa.String(40)),
        sa.Column("duplicate_reference_id", sa.Integer(), sa.ForeignKey("recall_targets.id", ondelete="SET NULL")),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_reason", sa.String(255)),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    )
    for column in ("batch_id", "original_order_no", "customer_name", "phone_normalized", "serial_number", "duplicate_flag", "review_required", "is_deleted"):
        op.create_index("ix_recall_targets_{}".format(column), "recall_targets", [column])


def downgrade():
    op.drop_table("recall_targets")
    op.drop_table("recall_target_upload_batches")
