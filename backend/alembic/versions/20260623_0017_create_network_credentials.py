"""create network credentials

Revision ID: 20260623_0017
Revises: 20260622_0016
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260623_0017"
down_revision = "20260622_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), server_default="기타", nullable=False),
        sa.Column("service_name", sa.String(length=200), nullable=False),
        sa.Column("internal_url", sa.String(length=500), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("port", sa.String(length=40), nullable=True),
        sa.Column("username", sa.String(length=200), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("importance", sa.String(length=20), server_default="일반", nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_credentials_id"), "network_credentials", ["id"], unique=False)
    op.create_index(
        op.f("ix_network_credentials_category"),
        "network_credentials",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_credentials_importance"),
        "network_credentials",
        ["importance"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_credentials_is_active"),
        "network_credentials",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_credentials_service_name"),
        "network_credentials",
        ["service_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_network_credentials_service_name"), table_name="network_credentials")
    op.drop_index(op.f("ix_network_credentials_is_active"), table_name="network_credentials")
    op.drop_index(op.f("ix_network_credentials_importance"), table_name="network_credentials")
    op.drop_index(op.f("ix_network_credentials_category"), table_name="network_credentials")
    op.drop_index(op.f("ix_network_credentials_id"), table_name="network_credentials")
    op.drop_table("network_credentials")
