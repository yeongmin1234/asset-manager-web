"""create audit logs

Revision ID: 20260714_0031
Revises: 20260714_0030
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0031"
down_revision = "20260714_0030"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("user_name", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("menu_key", sa.String(50), nullable=False),
        sa.Column("menu_name", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("target_name", sa.String(200), nullable=True),
        sa.Column("action_summary", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("access_type", sa.String(20), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser", sa.String(50), nullable=True),
        sa.Column("operating_system", sa.String(50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("occurred_at", "user_id", "username", "action_type", "menu_key", "target_type", "access_type"):
        op.create_index("ix_audit_logs_{}".format(column), "audit_logs", [column])


def downgrade():
    for column in reversed(("occurred_at", "user_id", "username", "action_type", "menu_key", "target_type", "access_type")):
        op.drop_index("ix_audit_logs_{}".format(column), table_name="audit_logs")
    op.drop_table("audit_logs")
