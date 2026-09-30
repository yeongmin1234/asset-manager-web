"""Record who soft deleted recall targets and why.

Revision ID: 20260930_0045
Revises: 20260930_0044
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0045"
down_revision = "20260930_0044"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_targets", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_targets", sa.Column("deleted_by", sa.Integer(), nullable=True))
    op.add_column("recall_targets", sa.Column("delete_reason", sa.String(255), nullable=True))
    op.create_foreign_key("fk_recall_target_deleted_by", "recall_targets", "users", ["deleted_by"], ["id"], ondelete="SET NULL")


def downgrade():
    op.drop_constraint("fk_recall_target_deleted_by", "recall_targets", type_="foreignkey")
    op.drop_column("recall_targets", "delete_reason")
    op.drop_column("recall_targets", "deleted_by")
    op.drop_column("recall_targets", "deleted_at")
