"""Add standalone auth without altering any existing public table or user data."""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0014"
down_revision = "20261027_0013"
branch_labels = None
depends_on = None


def upgrade():
    # DBA creates the dedicated login separately; no passwords belong in migrations.
    op.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='new_scm_auth' AND rolcanlogin
            AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)
            AND NOT EXISTS (SELECT FROM pg_auth_members WHERE member=pg_roles.oid))
        THEN RAISE EXCEPTION 'auth_role_missing_or_unsafe'; END IF;
        IF has_schema_privilege('new_scm_auth','public','CREATE')
            OR has_database_privilege('new_scm_auth',current_database(),'CREATE')
        THEN RAISE EXCEPTION 'auth_role_has_create_privileges'; END IF;
        END $$""")
    op.execute("CREATE SCHEMA scm_auth")
    op.execute("REVOKE ALL ON SCHEMA scm_auth FROM PUBLIC")
    op.create_table("credentials",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("public.users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("password_hash LIKE '$argon2id$%'", name="argon2id_only"), schema="scm_auth")
    op.create_table("sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("scm_auth.credentials.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name="session_expiry"), schema="scm_auth")
    op.create_index("ix_auth_sessions_user", "sessions", ["user_id"], schema="scm_auth")
    op.create_index("ix_auth_sessions_expiry", "sessions", ["expires_at"], schema="scm_auth")
    op.create_table("login_limits",
        sa.Column("bucket_key", sa.String(80), primary_key=True),
        sa.Column("window_id", sa.BigInteger(), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False), schema="scm_auth")
    op.create_index("ix_auth_limits_expiry", "login_limits", ["expires_at"], schema="scm_auth")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA scm_auth FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA public, scm_auth TO new_scm_auth")
    op.execute("GRANT SELECT (id,username,name,account_type,status) ON public.users TO new_scm_auth")
    op.execute("GRANT SELECT ON public.scm_user_grants TO new_scm_auth")
    op.execute("GRANT SELECT ON public.alembic_version TO new_scm_auth")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scm_auth TO new_scm_auth")


def downgrade():
    # Never silently destroy passwords or active sessions during a code rollback.
    raise RuntimeError("standalone_auth_downgrade_requires_reviewed_backup_restore")
