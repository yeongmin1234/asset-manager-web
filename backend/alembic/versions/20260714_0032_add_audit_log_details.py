"""add audit log details

Revision ID: 20260714_0032
Revises: 20260714_0031
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0032"
down_revision = "20260714_0031"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_logs", sa.Column("before_data", sa.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("after_data", sa.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("changed_fields", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("audit_logs", "changed_fields")
    op.drop_column("audit_logs", "after_data")
    op.drop_column("audit_logs", "before_data")
