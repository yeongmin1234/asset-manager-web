"""Add recall SCM order status and export batches.

Revision ID: 20260929_0039
Revises: 20260928_0038
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0039"
down_revision = "20260928_0038"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recall_order_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("total_quantity", sa.Integer(), nullable=False),
        sa.Column("file_content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_recall_order_batches_created_by", "recall_order_batches", ["created_by"])
    op.add_column("recall_applications", sa.Column("order_status", sa.String(40), nullable=False, server_default="ORDER_PENDING"))
    op.add_column("recall_applications", sa.Column("order_exported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_applications", sa.Column("order_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_applications", sa.Column(
        "order_batch_id", sa.Integer(), sa.ForeignKey("recall_order_batches.id", ondelete="RESTRICT"), nullable=True,
    ))
    op.create_index("ix_recall_applications_order_status", "recall_applications", ["order_status"])
    op.create_index("ix_recall_applications_order_batch_id", "recall_applications", ["order_batch_id"])


def downgrade():
    op.drop_index("ix_recall_applications_order_batch_id", table_name="recall_applications")
    op.drop_index("ix_recall_applications_order_status", table_name="recall_applications")
    op.drop_column("recall_applications", "order_batch_id")
    op.drop_column("recall_applications", "order_confirmed_at")
    op.drop_column("recall_applications", "order_exported_at")
    op.drop_column("recall_applications", "order_status")
    op.drop_table("recall_order_batches")
