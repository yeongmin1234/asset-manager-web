"""create sidebar menu labels

Revision ID: 20260714_0033
Revises: 20260714_0032
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0033"
down_revision = "20260714_0032"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sidebar_menu_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_key", sa.String(length=50), nullable=False),
        sa.Column("menu_name", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("menu_key"),
    )
    op.create_index("ix_sidebar_menu_labels_menu_key", "sidebar_menu_labels", ["menu_key"], unique=True)


def downgrade():
    op.drop_index("ix_sidebar_menu_labels_menu_key", table_name="sidebar_menu_labels")
    op.drop_table("sidebar_menu_labels")
