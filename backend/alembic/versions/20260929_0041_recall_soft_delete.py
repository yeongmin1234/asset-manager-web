"""Soft delete recall applications without erasing upload or status history.

Revision ID: 20260929_0041
Revises: 20260929_0040
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0041"
down_revision = "20260929_0040"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_applications", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("recall_applications", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_applications", sa.Column("deleted_by", sa.Integer(), nullable=True))
    op.add_column("recall_applications", sa.Column("delete_reason", sa.String(255), nullable=True))
    op.create_index("ix_recall_applications_is_deleted", "recall_applications", ["is_deleted"])
    op.create_foreign_key("fk_recall_application_deleted_by", "recall_applications", "users", ["deleted_by"], ["id"], ondelete="SET NULL")


def downgrade():
    op.drop_constraint("fk_recall_application_deleted_by", "recall_applications", type_="foreignkey")
    op.drop_index("ix_recall_applications_is_deleted", table_name="recall_applications")
    op.drop_column("recall_applications", "delete_reason")
    op.drop_column("recall_applications", "deleted_by")
    op.drop_column("recall_applications", "deleted_at")
    op.drop_column("recall_applications", "is_deleted")
