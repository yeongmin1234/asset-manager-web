"""create users

Revision ID: 20260709_0023
Revises: 20260706_0022
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0023"
down_revision = "20260706_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
