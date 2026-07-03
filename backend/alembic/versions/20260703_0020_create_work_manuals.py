"""create work manuals

Revision ID: 20260703_0020
Revises: 20260625_0019
Create Date: 2026-07-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260703_0020"
down_revision = "20260625_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_manuals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=80), server_default="일반", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=80), server_default="관리자", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("view_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_work_manuals_id"), "work_manuals", ["id"], unique=False)
    op.create_index(op.f("ix_work_manuals_category"), "work_manuals", ["category"], unique=False)
    op.create_index(op.f("ix_work_manuals_title"), "work_manuals", ["title"], unique=False)
    op.create_index(op.f("ix_work_manuals_is_pinned"), "work_manuals", ["is_pinned"], unique=False)
    op.create_index(op.f("ix_work_manuals_is_active"), "work_manuals", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_work_manuals_is_active"), table_name="work_manuals")
    op.drop_index(op.f("ix_work_manuals_is_pinned"), table_name="work_manuals")
    op.drop_index(op.f("ix_work_manuals_title"), table_name="work_manuals")
    op.drop_index(op.f("ix_work_manuals_category"), table_name="work_manuals")
    op.drop_index(op.f("ix_work_manuals_id"), table_name="work_manuals")
    op.drop_table("work_manuals")
