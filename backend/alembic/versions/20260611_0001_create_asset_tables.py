"""create asset tables

Revision ID: 20260611_0001
Revises:
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260611_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


asset_status = postgresql.ENUM(
    "사용중",
    "미사용",
    "폐기",
    name="asset_status",
    create_type=False,
)
asset_action_type = postgresql.ENUM(
    "등록",
    "수정",
    "상태변경",
    "폐기",
    "삭제",
    name="asset_action_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    asset_status.create(bind, checkfirst=True)
    asset_action_type.create(bind, checkfirst=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_departments_id"), "departments", ["id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("user_name", sa.String(length=100), nullable=True),
        sa.Column("status", asset_status, nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_category_id"), "assets", ["category_id"], unique=False)
    op.create_index(op.f("ix_assets_deleted_at"), "assets", ["deleted_at"], unique=False)
    op.create_index(
        op.f("ix_assets_department_id"),
        "assets",
        ["department_id"],
        unique=False,
    )
    op.create_index(op.f("ix_assets_id"), "assets", ["id"], unique=False)
    op.create_index(
        op.f("ix_assets_serial_number"),
        "assets",
        ["serial_number"],
        unique=False,
    )

    op.create_table(
        "asset_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("action_type", asset_action_type, nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_history_asset_id"),
        "asset_history",
        ["asset_id"],
        unique=False,
    )
    op.create_index(op.f("ix_asset_history_id"), "asset_history", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_history_id"), table_name="asset_history")
    op.drop_index(op.f("ix_asset_history_asset_id"), table_name="asset_history")
    op.drop_table("asset_history")

    op.drop_index(op.f("ix_assets_serial_number"), table_name="assets")
    op.drop_index(op.f("ix_assets_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_department_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_deleted_at"), table_name="assets")
    op.drop_index(op.f("ix_assets_category_id"), table_name="assets")
    op.drop_table("assets")

    op.drop_index(op.f("ix_departments_id"), table_name="departments")
    op.drop_table("departments")

    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")

    bind = op.get_bind()
    asset_action_type.drop(bind, checkfirst=True)
    asset_status.drop(bind, checkfirst=True)
