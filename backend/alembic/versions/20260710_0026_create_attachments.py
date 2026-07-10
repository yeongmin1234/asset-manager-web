"""create attachments

Revision ID: 20260710_0026
Revises: 20260710_0025
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260710_0026"
down_revision = "20260710_0025"
branch_labels = None
depends_on = None


attachment_entity_type = postgresql.ENUM(
    "asset",
    "vendor_contact",
    "work_manual",
    "company_car",
    "fire_insurance",
    "expiration_schedule",
    name="attachment_entity_type",
)

attachment_entity_type_column = postgresql.ENUM(
    "asset",
    "vendor_contact",
    "work_manual",
    "company_car",
    "fire_insurance",
    "expiration_schedule",
    name="attachment_entity_type",
    create_type=False,
)


def upgrade():
    bind = op.get_bind()
    attachment_entity_type.create(bind, checkfirst=True)
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", attachment_entity_type_column, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attachments_id"), "attachments", ["id"], unique=False)
    op.create_index(op.f("ix_attachments_entity_type"), "attachments", ["entity_type"], unique=False)
    op.create_index(op.f("ix_attachments_entity_id"), "attachments", ["entity_id"], unique=False)
    op.create_index("ix_attachments_entity", "attachments", ["entity_type", "entity_id"], unique=False)


def downgrade():
    op.drop_index("ix_attachments_entity", table_name="attachments")
    op.drop_index(op.f("ix_attachments_entity_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_entity_type"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_id"), table_name="attachments")
    op.drop_table("attachments")
    attachment_entity_type.drop(op.get_bind(), checkfirst=True)
