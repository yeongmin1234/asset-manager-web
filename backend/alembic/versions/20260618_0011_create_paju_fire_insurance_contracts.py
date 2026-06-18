"""create paju fire insurance contracts

Revision ID: 20260618_0011
Revises: 20260617_0010
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0011"
down_revision = "20260617_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paju_fire_insurance_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_group", sa.String(length=50), nullable=True),
        sa.Column("warehouse_name", sa.String(length=100), nullable=True),
        sa.Column("insurer_name", sa.String(length=100), nullable=True),
        sa.Column("contractor", sa.String(length=100), nullable=True),
        sa.Column("building_coverage", sa.String(length=100), nullable=True),
        sa.Column("inventory_coverage", sa.String(length=100), nullable=True),
        sa.Column("facility_coverage", sa.String(length=100), nullable=True),
        sa.Column("liability_coverage", sa.String(length=150), nullable=True),
        sa.Column("monthly_premium", sa.Numeric(14, 0), nullable=True),
        sa.Column("annual_premium", sa.Numeric(14, 0), nullable=True),
        sa.Column("contract_start_date", sa.Date(), nullable=True),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
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
    op.create_index(
        op.f("ix_paju_fire_insurance_contracts_id"),
        "paju_fire_insurance_contracts",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paju_fire_insurance_contracts_location_group"),
        "paju_fire_insurance_contracts",
        ["location_group"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paju_fire_insurance_contracts_warehouse_name"),
        "paju_fire_insurance_contracts",
        ["warehouse_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paju_fire_insurance_contracts_insurer_name"),
        "paju_fire_insurance_contracts",
        ["insurer_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paju_fire_insurance_contracts_contractor"),
        "paju_fire_insurance_contracts",
        ["contractor"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_paju_fire_insurance_contracts_contractor"),
        table_name="paju_fire_insurance_contracts",
    )
    op.drop_index(
        op.f("ix_paju_fire_insurance_contracts_insurer_name"),
        table_name="paju_fire_insurance_contracts",
    )
    op.drop_index(
        op.f("ix_paju_fire_insurance_contracts_warehouse_name"),
        table_name="paju_fire_insurance_contracts",
    )
    op.drop_index(
        op.f("ix_paju_fire_insurance_contracts_location_group"),
        table_name="paju_fire_insurance_contracts",
    )
    op.drop_index(
        op.f("ix_paju_fire_insurance_contracts_id"),
        table_name="paju_fire_insurance_contracts",
    )
    op.drop_table("paju_fire_insurance_contracts")
