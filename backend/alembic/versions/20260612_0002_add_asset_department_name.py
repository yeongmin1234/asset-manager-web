"""add asset department name

Revision ID: 20260612_0002
Revises: 20260611_0001
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_0002"
down_revision: str | None = "20260611_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("department_name", sa.String(length=100), nullable=True))
    op.execute(
        """
        UPDATE assets
        SET department_name = departments.name
        FROM departments
        WHERE assets.department_id = departments.id
          AND assets.department_name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("assets", "department_name")
