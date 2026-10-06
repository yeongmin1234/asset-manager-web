"""Create SCM preview activity log.

Revision ID: 20261006_0050
Revises: 20261006_0049
"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0050"
down_revision = "20261006_0049"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scm_activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("message", sa.String(length=120), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for name in ("user_id", "module", "action", "created_at"):
        op.create_index(f"ix_scm_activity_logs_{name}", "scm_activity_logs", [name])


def downgrade():
    for name in ("created_at", "action", "module", "user_id"):
        op.drop_index(f"ix_scm_activity_logs_{name}", table_name="scm_activity_logs")
    op.drop_table("scm_activity_logs")
