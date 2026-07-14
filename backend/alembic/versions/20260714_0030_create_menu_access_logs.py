"""create menu access logs

Revision ID: 20260714_0030
Revises: 20260714_0029
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_0030"
down_revision = "20260714_0029"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "menu_access_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=True),
        sa.Column("menu_key", sa.String(length=50), nullable=False),
        sa.Column("menu_name", sa.String(length=100), nullable=False),
        sa.Column("route_path", sa.String(length=200), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("access_type", sa.String(length=20), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser", sa.String(length=50), nullable=True),
        sa.Column("operating_system", sa.String(length=50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_access_logs_occurred_at", "menu_access_logs", ["occurred_at"])
    op.create_index("ix_menu_access_logs_user_id", "menu_access_logs", ["user_id"])
    op.create_index("ix_menu_access_logs_username", "menu_access_logs", ["username"])
    op.create_index("ix_menu_access_logs_menu_key", "menu_access_logs", ["menu_key"])
    op.create_index("ix_menu_access_logs_access_type", "menu_access_logs", ["access_type"])


def downgrade():
    op.drop_index("ix_menu_access_logs_access_type", table_name="menu_access_logs")
    op.drop_index("ix_menu_access_logs_menu_key", table_name="menu_access_logs")
    op.drop_index("ix_menu_access_logs_username", table_name="menu_access_logs")
    op.drop_index("ix_menu_access_logs_user_id", table_name="menu_access_logs")
    op.drop_index("ix_menu_access_logs_occurred_at", table_name="menu_access_logs")
    op.drop_table("menu_access_logs")
