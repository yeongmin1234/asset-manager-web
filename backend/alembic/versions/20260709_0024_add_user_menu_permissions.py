"""add user menu permissions

Revision ID: 20260709_0024
Revises: 20260709_0023
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0024"
down_revision = "20260709_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "menu_permissions",
            sa.JSON(),
            nullable=False,
            server_default='["dashboard", "assets"]',
        ),
    )


def downgrade():
    op.drop_column("users", "menu_permissions")
