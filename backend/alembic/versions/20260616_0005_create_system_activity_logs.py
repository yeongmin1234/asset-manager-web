"""create system activity logs

Revision ID: 20260616_0005
Revises: 20260616_0004
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260616_0005"
down_revision = "20260616_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_name", sa.String(length=100), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("target_name", sa.String(length=200), nullable=True),
        sa.Column("actor_ip", sa.String(length=100), nullable=True),
        sa.Column("actor_name", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_system_activity_logs_action_type"),
        "system_activity_logs",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_activity_logs_created_at"),
        "system_activity_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_activity_logs_id"),
        "system_activity_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_activity_logs_menu_name"),
        "system_activity_logs",
        ["menu_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_activity_logs_target_id"),
        "system_activity_logs",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_activity_logs_target_type"),
        "system_activity_logs",
        ["target_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_system_activity_logs_target_type"), table_name="system_activity_logs")
    op.drop_index(op.f("ix_system_activity_logs_target_id"), table_name="system_activity_logs")
    op.drop_index(op.f("ix_system_activity_logs_menu_name"), table_name="system_activity_logs")
    op.drop_index(op.f("ix_system_activity_logs_id"), table_name="system_activity_logs")
    op.drop_index(op.f("ix_system_activity_logs_created_at"), table_name="system_activity_logs")
    op.drop_index(op.f("ix_system_activity_logs_action_type"), table_name="system_activity_logs")
    op.drop_table("system_activity_logs")
