"""create company vehicles

Revision ID: 20260616_0006
Revises: 20260616_0005
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260616_0006"
down_revision = "20260616_0005"
branch_labels = None
depends_on = None


vehicle_ownership_type = postgresql.ENUM(
    "회사",
    "리스",
    name="vehicle_ownership_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    vehicle_ownership_type.create(bind, checkfirst=True)

    op.create_table(
        "company_vehicles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=100), nullable=True),
        sa.Column("vehicle_number", sa.String(length=50), nullable=False),
        sa.Column("vehicle_name", sa.String(length=100), nullable=False),
        sa.Column("driver_name", sa.String(length=100), nullable=True),
        sa.Column("ownership_type", vehicle_ownership_type, nullable=False),
        sa.Column("insurance_company", sa.String(length=100), nullable=True),
        sa.Column("insurance_type", sa.String(length=100), nullable=True),
        sa.Column("insurance_start_date", sa.Date(), nullable=True),
        sa.Column("insurance_end_date", sa.Date(), nullable=True),
        sa.Column("lease_company", sa.String(length=100), nullable=True),
        sa.Column("lease_start_date", sa.Date(), nullable=True),
        sa.Column("lease_end_date", sa.Date(), nullable=True),
        sa.Column("monthly_lease_amount", sa.Numeric(14, 0), nullable=True),
        sa.Column("lease_payment_day", sa.String(length=50), nullable=True),
        sa.Column("tax_note", sa.Text(), nullable=True),
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
    op.create_index(op.f("ix_company_vehicles_id"), "company_vehicles", ["id"], unique=False)
    op.create_index(
        op.f("ix_company_vehicles_vehicle_name"),
        "company_vehicles",
        ["vehicle_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_vehicles_vehicle_number"),
        "company_vehicles",
        ["vehicle_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_company_vehicles_vehicle_number"), table_name="company_vehicles")
    op.drop_index(op.f("ix_company_vehicles_vehicle_name"), table_name="company_vehicles")
    op.drop_index(op.f("ix_company_vehicles_id"), table_name="company_vehicles")
    op.drop_table("company_vehicles")

    bind = op.get_bind()
    vehicle_ownership_type.drop(bind, checkfirst=True)
