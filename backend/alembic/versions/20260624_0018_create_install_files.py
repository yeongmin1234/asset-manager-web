"""create install files table

Revision ID: 20260624_0018
Revises: 20260623_0017
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0018"
down_revision: Union[str, None] = "20260623_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "install_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("os_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("install_guide", sa.Text(), nullable=True),
        sa.Column("caution_note", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("install_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_index(op.f("ix_install_files_id"), "install_files", ["id"], unique=False)
    op.create_index(op.f("ix_install_files_title"), "install_files", ["title"], unique=False)
    op.create_index(op.f("ix_install_files_category"), "install_files", ["category"], unique=False)
    op.create_index(op.f("ix_install_files_os_type"), "install_files", ["os_type"], unique=False)
    op.create_index(op.f("ix_install_files_is_required"), "install_files", ["is_required"], unique=False)
    op.create_index(op.f("ix_install_files_install_order"), "install_files", ["install_order"], unique=False)
    op.create_index(op.f("ix_install_files_is_active"), "install_files", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_install_files_is_active"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_install_order"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_is_required"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_os_type"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_category"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_title"), table_name="install_files")
    op.drop_index(op.f("ix_install_files_id"), table_name="install_files")
    op.drop_table("install_files")
