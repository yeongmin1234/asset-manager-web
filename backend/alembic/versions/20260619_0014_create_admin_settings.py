"""create admin settings

Revision ID: 20260619_0014
Revises: 20260618_0013
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0014"
down_revision = "20260618_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_settings_id"), "admin_settings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_settings_id"), table_name="admin_settings")
    op.drop_table("admin_settings")
