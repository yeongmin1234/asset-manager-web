"""create login access logs

Revision ID: 20260714_0029
Revises: 20260714_0028
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_0029"
down_revision = "20260714_0028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_access_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("login_result", sa.String(length=20), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("access_type", sa.String(length=20), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser", sa.String(length=50), nullable=True),
        sa.Column("operating_system", sa.String(length=50), nullable=True),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_access_logs_user_id", "login_access_logs", ["user_id"])
    op.create_index("ix_login_access_logs_username", "login_access_logs", ["username"])
    op.create_index("ix_login_access_logs_login_result", "login_access_logs", ["login_result"])
    op.create_index("ix_login_access_logs_access_type", "login_access_logs", ["access_type"])
    op.create_index("ix_login_access_logs_occurred_at", "login_access_logs", ["occurred_at"])


def downgrade():
    op.drop_index("ix_login_access_logs_occurred_at", table_name="login_access_logs")
    op.drop_index("ix_login_access_logs_access_type", table_name="login_access_logs")
    op.drop_index("ix_login_access_logs_login_result", table_name="login_access_logs")
    op.drop_index("ix_login_access_logs_username", table_name="login_access_logs")
    op.drop_index("ix_login_access_logs_user_id", table_name="login_access_logs")
    op.drop_table("login_access_logs")
