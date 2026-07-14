"""create hr accounts

Revision ID: 20260714_0028
Revises: 20260710_0027
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0028"
down_revision = "20260710_0027"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hr_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("dowoffice", sa.String(length=200), nullable=True),
        sa.Column("erp", sa.String(length=200), nullable=True),
        sa.Column("scm", sa.String(length=200), nullable=True),
        sa.Column("nas", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hr_accounts_department", "hr_accounts", ["department"])
    op.create_index("ix_hr_accounts_name", "hr_accounts", ["name"])
    op.create_index("ix_hr_accounts_deleted_at", "hr_accounts", ["deleted_at"])


def downgrade():
    op.drop_index("ix_hr_accounts_deleted_at", table_name="hr_accounts")
    op.drop_index("ix_hr_accounts_name", table_name="hr_accounts")
    op.drop_index("ix_hr_accounts_department", table_name="hr_accounts")
    op.drop_table("hr_accounts")
