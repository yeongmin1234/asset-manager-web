"""normalize user menu permission keys

Revision ID: 20260710_0027
Revises: 20260710_0026
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_0027"
down_revision = "20260710_0026"
branch_labels = None
depends_on = None


LEGACY_TO_CANONICAL = {
    "beverage-orders": "drink_orders",
    "work-manuals": "work_manual",
    "vendor-contacts": "vendor_contacts",
    "vehicles": "company_cars",
    "paju-fire-insurance": "fire_insurance",
    "stats": "statistics",
    "history": "changelog",
}


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, menu_permissions FROM users")).fetchall()
    update_statement = sa.text(
        "UPDATE users SET menu_permissions = :permissions WHERE id = :user_id"
    ).bindparams(sa.bindparam("permissions", type_=sa.JSON()))
    for user_id, permissions in rows:
        if not isinstance(permissions, list):
            continue
        normalized = list(dict.fromkeys(LEGACY_TO_CANONICAL.get(value, value) for value in permissions))
        if normalized != permissions:
            connection.execute(update_statement, {"permissions": normalized, "user_id": user_id})


def downgrade():
    canonical_to_legacy = {value: key for key, value in LEGACY_TO_CANONICAL.items()}
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, menu_permissions FROM users")).fetchall()
    update_statement = sa.text(
        "UPDATE users SET menu_permissions = :permissions WHERE id = :user_id"
    ).bindparams(sa.bindparam("permissions", type_=sa.JSON()))
    for user_id, permissions in rows:
        if not isinstance(permissions, list):
            continue
        restored = list(dict.fromkeys(canonical_to_legacy.get(value, value) for value in permissions))
        if restored != permissions:
            connection.execute(update_statement, {"permissions": restored, "user_id": user_id})
