"""split network menu permissions

Revision ID: 20260714_0035
Revises: 20260714_0034
"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_0035"
down_revision = "20260714_0034"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, menu_permissions FROM users")).fetchall()
    update_users = sa.text("UPDATE users SET menu_permissions = :permissions WHERE id = :user_id").bindparams(sa.bindparam("permissions", type_=sa.JSON()))
    for user_id, permissions in rows:
        if not isinstance(permissions, list) or "network" not in permissions:
            continue
        migrated = []
        for value in permissions:
            if value == "network":
                migrated.extend(["access_info", "equipment_status"])
            else:
                migrated.append(value)
        connection.execute(update_users, {"permissions": list(dict.fromkeys(migrated)), "user_id": user_id})

    old_visibility = connection.execute(sa.text("SELECT visible FROM menu_visibility_settings WHERE menu_key = 'network'")).scalar()
    if old_visibility is not None:
        for menu_key in ("access_info", "equipment_status"):
            exists = connection.execute(sa.text("SELECT 1 FROM menu_visibility_settings WHERE menu_key = :menu_key"), {"menu_key": menu_key}).scalar()
            if not exists:
                connection.execute(sa.text("INSERT INTO menu_visibility_settings (menu_key, visible) VALUES (:menu_key, :visible)"), {"menu_key": menu_key, "visible": old_visibility})


def downgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, menu_permissions FROM users")).fetchall()
    update_users = sa.text("UPDATE users SET menu_permissions = :permissions WHERE id = :user_id").bindparams(sa.bindparam("permissions", type_=sa.JSON()))
    for user_id, permissions in rows:
        if not isinstance(permissions, list):
            continue
        if "access_info" in permissions or "equipment_status" in permissions:
            restored = [value for value in permissions if value not in ("access_info", "equipment_status")]
            restored.append("network")
            connection.execute(update_users, {"permissions": list(dict.fromkeys(restored)), "user_id": user_id})
    connection.execute(sa.text("DELETE FROM menu_visibility_settings WHERE menu_key IN ('access_info', 'equipment_status')"))
