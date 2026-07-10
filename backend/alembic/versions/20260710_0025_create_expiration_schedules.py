"""create expiration schedules

Revision ID: 20260710_0025
Revises: 20260709_0024
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260710_0025"
down_revision = "20260709_0024"
branch_labels = None
depends_on = None


expiration_schedule_category = postgresql.ENUM(
    "vehicle_insurance",
    "vehicle_inspection",
    "fire_insurance",
    "contract",
    "rental",
    "software_license",
    "warranty",
    "server_maintenance",
    "nas_maintenance",
    "other",
    name="expiration_schedule_category",
)

expiration_schedule_status = postgresql.ENUM(
    "overdue",
    "within_7_days",
    "within_30_days",
    "normal",
    "completed",
    name="expiration_schedule_status",
)

expiration_schedule_category_column = postgresql.ENUM(
    "vehicle_insurance",
    "vehicle_inspection",
    "fire_insurance",
    "contract",
    "rental",
    "software_license",
    "warranty",
    "server_maintenance",
    "nas_maintenance",
    "other",
    name="expiration_schedule_category",
    create_type=False,
)

expiration_schedule_status_column = postgresql.ENUM(
    "overdue",
    "within_7_days",
    "within_30_days",
    "normal",
    "completed",
    name="expiration_schedule_status",
    create_type=False,
)


def upgrade():
    bind = op.get_bind()
    expiration_schedule_category.create(bind, checkfirst=True)
    expiration_schedule_status.create(bind, checkfirst=True)

    op.create_table(
        "expiration_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", expiration_schedule_category_column, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_name", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("notification_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("status", expiration_schedule_status_column, server_default="normal", nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expiration_schedules_id"), "expiration_schedules", ["id"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_category"), "expiration_schedules", ["category"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_title"), "expiration_schedules", ["title"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_target_name"), "expiration_schedules", ["target_name"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_due_date"), "expiration_schedules", ["due_date"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_status"), "expiration_schedules", ["status"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_source_type"), "expiration_schedules", ["source_type"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_source_id"), "expiration_schedules", ["source_id"], unique=False)
    op.create_index(op.f("ix_expiration_schedules_is_completed"), "expiration_schedules", ["is_completed"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_expiration_schedules_is_completed"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_source_id"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_source_type"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_status"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_due_date"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_target_name"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_title"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_category"), table_name="expiration_schedules")
    op.drop_index(op.f("ix_expiration_schedules_id"), table_name="expiration_schedules")
    op.drop_table("expiration_schedules")
    expiration_schedule_status.drop(op.get_bind(), checkfirst=True)
    expiration_schedule_category.drop(op.get_bind(), checkfirst=True)
