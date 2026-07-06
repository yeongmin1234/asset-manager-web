"""create vendor contacts

Revision ID: 20260706_0021
Revises: 20260703_0020
Create Date: 2026-07-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260706_0021"
down_revision = "20260703_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), server_default="기타", nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=True),
        sa.Column("manager_name", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_contacts_id"), "vendor_contacts", ["id"], unique=False)
    op.create_index(op.f("ix_vendor_contacts_category"), "vendor_contacts", ["category"], unique=False)
    op.create_index(op.f("ix_vendor_contacts_company_name"), "vendor_contacts", ["company_name"], unique=False)
    op.create_index(op.f("ix_vendor_contacts_is_deleted"), "vendor_contacts", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vendor_contacts_is_deleted"), table_name="vendor_contacts")
    op.drop_index(op.f("ix_vendor_contacts_company_name"), table_name="vendor_contacts")
    op.drop_index(op.f("ix_vendor_contacts_category"), table_name="vendor_contacts")
    op.drop_index(op.f("ix_vendor_contacts_id"), table_name="vendor_contacts")
    op.drop_table("vendor_contacts")
