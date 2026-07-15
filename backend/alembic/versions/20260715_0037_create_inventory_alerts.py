"""create inventory alert rules and alerts

Revision ID: 20260715_0037
Revises: 20260715_0036
"""
from alembic import op
import sqlalchemy as sa

revision = "20260715_0037"
down_revision = "20260715_0036"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("item_code", sa.String(20), nullable=True),
        sa.Column("threshold_quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("threshold_change_quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("threshold_change_rate", sa.Numeric(12, 4), nullable=True),
        sa.Column("comparison_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("severity", sa.String(16), server_default="warning", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("alert_type IN ('OUT_OF_STOCK','LOW_STOCK','NEGATIVE_STOCK','RAPID_DECREASE')", name="ck_inventory_alert_rule_type"),
        sa.CheckConstraint("severity IN ('info','warning','critical')", name="ck_inventory_alert_rule_severity"),
    )
    for col in ("id", "alert_type", "item_code", "is_active", "severity"):
        op.create_index("ix_inventory_alert_rules_{}".format(col), "inventory_alert_rules", [col])

    op.create_table(
        "inventory_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("inventory_alert_rules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_code", sa.String(20), nullable=False),
        sa.Column("item_name", sa.String(300), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("inventory_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("current_quantity", sa.Numeric(30, 10), nullable=False),
        sa.Column("change_quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("change_rate", sa.Numeric(12, 4), nullable=True),
        sa.Column("threshold_description", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(100), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("partial_result", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("safe_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active','acknowledged','resolved')", name="ck_inventory_alert_status"),
    )
    for col in ("id", "alert_type", "severity", "rule_id", "item_code", "detected_at", "status"):
        op.create_index("ix_inventory_alerts_{}".format(col), "inventory_alerts", [col])
    op.create_index(
        "uq_inventory_alert_open_rule_item_type", "inventory_alerts",
        ["rule_id", "item_code", "alert_type"], unique=True,
        postgresql_where=sa.text("status IN ('active', 'acknowledged')"),
    )
    rules = sa.table(
        "inventory_alert_rules", sa.column("name"), sa.column("alert_type"),
        sa.column("threshold_quantity"), sa.column("threshold_change_quantity"),
        sa.column("threshold_change_rate"), sa.column("comparison_minutes"),
        sa.column("severity"), sa.column("is_active"),
    )
    op.bulk_insert(rules, [
        {"name": "전체 품목 품절", "alert_type": "OUT_OF_STOCK", "threshold_quantity": None, "threshold_change_quantity": None, "threshold_change_rate": None, "comparison_minutes": None, "severity": "critical", "is_active": True},
        {"name": "전체 품목 부족 재고", "alert_type": "LOW_STOCK", "threshold_quantity": 5, "threshold_change_quantity": None, "threshold_change_rate": None, "comparison_minutes": None, "severity": "warning", "is_active": True},
        {"name": "전체 품목 음수 재고", "alert_type": "NEGATIVE_STOCK", "threshold_quantity": None, "threshold_change_quantity": None, "threshold_change_rate": None, "comparison_minutes": None, "severity": "critical", "is_active": True},
        {"name": "전체 품목 급감", "alert_type": "RAPID_DECREASE", "threshold_quantity": None, "threshold_change_quantity": 20, "threshold_change_rate": 30, "comparison_minutes": 1440, "severity": "critical", "is_active": True},
    ])


def downgrade():
    op.drop_table("inventory_alerts")
    op.drop_table("inventory_alert_rules")
