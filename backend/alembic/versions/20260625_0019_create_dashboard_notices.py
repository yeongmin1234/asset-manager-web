"""create dashboard notices

Revision ID: 20260625_0019
Revises: 20260624_0018
Create Date: 2026-06-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0019"
down_revision = "20260624_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_notices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notice_type", sa.String(length=20), server_default="공지", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dashboard_notices_id"), "dashboard_notices", ["id"], unique=False)
    op.create_index(op.f("ix_dashboard_notices_notice_type"), "dashboard_notices", ["notice_type"], unique=False)
    op.create_index(op.f("ix_dashboard_notices_title"), "dashboard_notices", ["title"], unique=False)
    op.create_index(op.f("ix_dashboard_notices_is_pinned"), "dashboard_notices", ["is_pinned"], unique=False)
    op.create_index(op.f("ix_dashboard_notices_is_active"), "dashboard_notices", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_notices_is_active"), table_name="dashboard_notices")
    op.drop_index(op.f("ix_dashboard_notices_is_pinned"), table_name="dashboard_notices")
    op.drop_index(op.f("ix_dashboard_notices_title"), table_name="dashboard_notices")
    op.drop_index(op.f("ix_dashboard_notices_notice_type"), table_name="dashboard_notices")
    op.drop_index(op.f("ix_dashboard_notices_id"), table_name="dashboard_notices")
    op.drop_table("dashboard_notices")
