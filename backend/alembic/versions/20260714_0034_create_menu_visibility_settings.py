"""create menu visibility settings

Revision ID: 20260714_0034
Revises: 20260714_0033
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0034"
down_revision = "20260714_0033"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "menu_visibility_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_key", sa.String(length=50), nullable=False),
        sa.Column("visible", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("menu_key"),
    )
    op.create_index("ix_menu_visibility_settings_menu_key", "menu_visibility_settings", ["menu_key"], unique=True)


def downgrade():
    op.drop_index("ix_menu_visibility_settings_menu_key", table_name="menu_visibility_settings")
    op.drop_table("menu_visibility_settings")
