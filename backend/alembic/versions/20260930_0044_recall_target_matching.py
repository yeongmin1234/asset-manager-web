"""Add safe application matching state to raw recall targets.

Revision ID: 20260930_0044
Revises: 20260930_0043
"""

from alembic import op
import sqlalchemy as sa


revision = "20260930_0044"
down_revision = "20260930_0043"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_targets", sa.Column("match_status", sa.String(20), nullable=False, server_default="UNMATCHED"))
    op.add_column("recall_targets", sa.Column("matched_application_id", sa.Integer(), sa.ForeignKey("recall_applications.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("recall_targets", sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_targets", sa.Column("matched_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("recall_targets", sa.Column("match_method", sa.String(20), nullable=True))
    op.add_column("recall_targets", sa.Column("match_review_reason", sa.String(100), nullable=True))
    op.create_index("ix_recall_targets_match_status", "recall_targets", ["match_status"])
    op.create_index("ix_recall_targets_matched_application_id", "recall_targets", ["matched_application_id"], unique=True)


def downgrade():
    op.drop_index("ix_recall_targets_matched_application_id", table_name="recall_targets")
    op.drop_index("ix_recall_targets_match_status", table_name="recall_targets")
    for column in ("match_review_reason", "match_method", "matched_by", "matched_at", "matched_application_id", "match_status"):
        op.drop_column("recall_targets", column)
