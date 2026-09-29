"""Track duplicate recall applications without changing recall/order states.

Revision ID: 20260929_0040
Revises: 20260929_0039
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0040"
down_revision = "20260929_0039"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recall_applications", sa.Column("duplicate_flag", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("recall_applications", sa.Column("duplicate_reason", sa.String(40), nullable=True))
    op.add_column("recall_applications", sa.Column("duplicate_reference_id", sa.Integer(), nullable=True))
    op.add_column("recall_applications", sa.Column("duplicate_resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recall_applications", sa.Column("duplicate_resolved_by", sa.Integer(), nullable=True))
    op.add_column("recall_applications", sa.Column("duplicate_resolution", sa.String(40), nullable=True))
    op.create_index("ix_recall_applications_duplicate_flag", "recall_applications", ["duplicate_flag"])
    op.create_index("ix_recall_applications_duplicate_reference_id", "recall_applications", ["duplicate_reference_id"])
    op.create_foreign_key("fk_recall_application_duplicate_reference", "recall_applications", "recall_applications", ["duplicate_reference_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_recall_application_duplicate_resolver", "recall_applications", "users", ["duplicate_resolved_by"], ["id"], ondelete="SET NULL")
    op.create_table(
        "recall_duplicate_resolution_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recall_application_id", sa.Integer(), sa.ForeignKey("recall_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_recall_duplicate_resolution_history_recall_application_id", "recall_duplicate_resolution_history", ["recall_application_id"])


def downgrade():
    op.drop_index("ix_recall_duplicate_resolution_history_recall_application_id", table_name="recall_duplicate_resolution_history")
    op.drop_table("recall_duplicate_resolution_history")
    op.drop_constraint("fk_recall_application_duplicate_resolver", "recall_applications", type_="foreignkey")
    op.drop_constraint("fk_recall_application_duplicate_reference", "recall_applications", type_="foreignkey")
    op.drop_index("ix_recall_applications_duplicate_reference_id", table_name="recall_applications")
    op.drop_index("ix_recall_applications_duplicate_flag", table_name="recall_applications")
    for name in ("duplicate_resolution", "duplicate_resolved_by", "duplicate_resolved_at", "duplicate_reference_id", "duplicate_reason", "duplicate_flag"):
        op.drop_column("recall_applications", name)
