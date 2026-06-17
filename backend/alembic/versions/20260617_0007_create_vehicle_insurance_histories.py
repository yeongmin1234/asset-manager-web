"""create vehicle insurance histories

Revision ID: 20260617_0007
Revises: 20260616_0006
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0007"
down_revision = "20260616_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_insurance_histories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("insurance_type", sa.String(length=100), nullable=True),
        sa.Column("driver_name", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(14, 0), nullable=True),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["company_vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vehicle_insurance_histories_id"),
        "vehicle_insurance_histories",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_insurance_histories_vehicle_id"),
        "vehicle_insurance_histories",
        ["vehicle_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_vehicle_insurance_histories_vehicle_id"),
        table_name="vehicle_insurance_histories",
    )
    op.drop_index(
        op.f("ix_vehicle_insurance_histories_id"),
        table_name="vehicle_insurance_histories",
    )
    op.drop_table("vehicle_insurance_histories")
