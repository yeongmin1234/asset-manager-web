"""create software items

Revision ID: 20260615_0003
Revises: 20260612_0002
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260615_0003"
down_revision = "20260612_0002"
branch_labels = None
depends_on = None


software_license_type = postgresql.ENUM(
    "영구",
    "구독",
    "사용중지",
    name="software_license_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    software_license_type.create(bind, checkfirst=True)

    op.create_table(
        "software_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("license_type", software_license_type, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("expire_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_software_items_id"), "software_items", ["id"], unique=False)
    op.create_index(
        op.f("ix_software_items_name"),
        "software_items",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_software_items_name"), table_name="software_items")
    op.drop_index(op.f("ix_software_items_id"), table_name="software_items")
    op.drop_table("software_items")

    bind = op.get_bind()
    software_license_type.drop(bind, checkfirst=True)
