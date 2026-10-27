"""Explicit SCM identity mapping and user grants.

Revision ID: 20261027_0013
Revises: 20260729_0012

Downgrade drops these tables and permanently loses their mapping/grant records.
"""
from alembic import op
import sqlalchemy as sa


revision = "20261027_0013"
down_revision = "20260729_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scm_identity_mappings",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("issuer", sa.String(80), nullable=False),
        sa.Column("subject", sa.String(80), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("public.users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approved_by", sa.BigInteger(), sa.ForeignKey("public.users.id", ondelete="RESTRICT")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("issuer", "subject", name="uq_scm_identity"),
        sa.UniqueConstraint("user_id", name="uq_scm_mapped_user"),
        sa.CheckConstraint("issuer <> '' AND subject ~ '^[1-9][0-9]*$'", name="ck_scm_identity_subject"),
        sa.CheckConstraint("NOT is_active OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name="ck_scm_mapping_approval"),
        schema="public",
    )
    op.create_table(
        "scm_user_grants",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("grant_type", sa.String(10), primary_key=True),
        sa.Column("grant_name", sa.String(120), primary_key=True),
        sa.Column("approved_by", sa.BigInteger(), sa.ForeignKey("public.users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("grant_type IN ('menu', 'action')", name="ck_scm_grant_type"),
        sa.CheckConstraint("grant_name <> ''", name="ck_scm_grant_name"),
        schema="public",
    )
    op.execute("GRANT SELECT ON TABLE public.scm_identity_mappings, public.scm_user_grants TO new_scm_ro")


def downgrade():
    op.drop_table("scm_user_grants", schema="public")
    op.drop_table("scm_identity_mappings", schema="public")

