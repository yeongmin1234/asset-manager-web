"""create inventory snapshot scheduler tables

Revision ID: 20260715_0036
Revises: 20260714_0035
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0036"
down_revision = "20260714_0035"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("run_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Seoul", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("target_mode", sa.String(length=32), server_default="selected_items", nullable=False),
        sa.Column("target_item_codes", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_mode IN ('selected_items', 'all_supported_items')", name="ck_inventory_schedule_target_mode"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_schedules_id", "inventory_schedules", ["id"])
    op.create_index("ix_inventory_schedules_is_active", "inventory_schedules", ["is_active"])

    op.create_table(
        "inventory_job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_group_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requested_item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("snapshot_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('running', 'success', 'partial_success', 'failed', 'skipped')", name="ck_inventory_job_run_status"),
        sa.ForeignKeyConstraint(["schedule_id"], ["inventory_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "schedule_id", "snapshot_group_id", "started_at", "status"):
        op.create_index("ix_inventory_job_runs_{}".format(column), "inventory_job_runs", [column])

    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_group_id", sa.String(length=36), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_type", sa.String(length=16), nullable=False),
        sa.Column("item_code", sa.String(length=20), nullable=False),
        sa.Column("item_name", sa.String(length=300), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("warehouse_code", sa.String(length=20), server_default="", nullable=False),
        sa.Column("warehouse_name", sa.String(length=200), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=30, scale=10), nullable=False),
        sa.Column("total_quantity", sa.Numeric(precision=30, scale=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("row_type IN ('total', 'warehouse')", name="ck_inventory_snapshot_row_type"),
        sa.ForeignKeyConstraint(["schedule_id"], ["inventory_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_group_id", "item_code", "row_type", "warehouse_code",
            name="uq_inventory_snapshot_group_item_row_warehouse",
        ),
    )
    for column in ("id", "snapshot_group_id", "schedule_id", "snapshot_at", "row_type", "item_code", "item_name"):
        op.create_index("ix_inventory_snapshots_{}".format(column), "inventory_snapshots", [column])


def downgrade():
    op.drop_table("inventory_snapshots")
    op.drop_table("inventory_job_runs")
    op.drop_table("inventory_schedules")
