"""Read-only SQL policy checks shared by the host verifier and backend probe."""
from sqlalchemy import text
import re


def _check_expression(expression, allow_text_cast=False):
    # Keep SQL literal contents exact. Only the varchar password CHECK needs
    # PostgreSQL's implicit text casts normalized; expiry casts are forbidden.
    parts = re.split(r"('(?:[^']|'')*')", expression)
    pattern = r"\s+|[()]|::text" if allow_text_cast else r"\s+|[()]"
    return "".join(part if index % 2 else re.sub(pattern, "", part)
                   for index, part in enumerate(parts))


def verify_auth_schema(db):
    """Inspect catalogs only. Never select password/session values or test writes."""
    expected = {
        "credentials": {"user_id": "bigint", "password_hash": "character varying(512)",
                        "enabled": "boolean", "updated_at": "bigint"},
        "sessions": {"token_hash": "character varying(64)", "user_id": "bigint",
                     "created_at": "bigint", "expires_at": "bigint"},
        "login_limits": {"bucket_key": "character varying(80)", "window_id": "bigint",
                         "attempts": "integer", "expires_at": "bigint"},
    }
    columns = db.execute(text("""SELECT c.relname, a.attname, format_type(a.atttypid,a.atttypmod), a.attnotnull,
        pg_get_expr(d.adbin,d.adrelid)
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE n.nspname='scm_auth' AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped""")).all()
    wanted = {(table, name, kind, True, "false" if (table, name) == ("credentials", "enabled") else None)
              for table, fields in expected.items() for name, kind in fields.items()}
    if set(map(tuple, columns)) != wanted:
        raise ValueError("auth_schema_columns_invalid")
    primary = db.execute(text("""SELECT c.relname, ARRAY(SELECT a.attname FROM unnest(k.conkey)
        WITH ORDINALITY x(num,ord) JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=x.num ORDER BY x.ord)
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='scm_auth' AND k.contype='p' AND k.convalidated AND NOT k.condeferrable""")).all()
    if {table: tuple(keys) for table, keys in primary} != {
            "credentials": ("user_id",), "sessions": ("token_hash",), "login_limits": ("bucket_key", "window_id")}:
        raise ValueError("auth_schema_primary_keys_invalid")
    foreign = db.execute(text("""SELECT c.relname,a.attname,rn.nspname,r.relname,ra.attname,
        k.confdeltype,k.convalidated,k.condeferrable,cardinality(k.conkey),k.confupdtype FROM pg_constraint k
        JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_class r ON r.oid=k.confrelid JOIN pg_namespace rn ON rn.oid=r.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.conkey[1]
        JOIN pg_attribute ra ON ra.attrelid=r.oid AND ra.attnum=k.confkey[1]
        WHERE n.nspname='scm_auth' AND k.contype='f'""")).all()
    if set(map(tuple, foreign)) != {("credentials", "user_id", "public", "users", "id", "r", True, False, 1, "a"),
                                   ("sessions", "user_id", "scm_auth", "credentials", "user_id", "c", True, False, 1, "a")}:
        raise ValueError("auth_schema_foreign_keys_invalid")
    indexes = db.execute(text("""SELECT i.relname,c.relname,ARRAY(SELECT a.attname FROM unnest(x.indkey)
        WITH ORDINALITY u(num,ord) JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=u.num ORDER BY u.ord),
        x.indisvalid AND x.indisready AND NOT x.indisunique AND x.indpred IS NULL AND x.indexprs IS NULL AND am.amname='btree'
        FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_am am ON am.oid=i.relam
        WHERE n.nspname='scm_auth' AND NOT x.indisprimary""")).all()
    if {(name, table, tuple(keys), valid) for name, table, keys, valid in indexes} != {
            ("ix_auth_sessions_user", "sessions", ("user_id",), True),
            ("ix_auth_sessions_expiry", "sessions", ("expires_at",), True),
            ("ix_auth_limits_expiry", "login_limits", ("expires_at",), True)}:
        raise ValueError("auth_schema_indexes_invalid")
    checks = db.execute(text("""SELECT c.relname,k.conname,pg_get_expr(k.conbin,k.conrelid),k.convalidated
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='scm_auth' AND k.contype='c'""")).all()
    normalized = {(table, name, _check_expression(expression, name == "argon2id_only"), valid)
                  for table, name, expression, valid in checks}
    if normalized != {("credentials", "argon2id_only", "password_hash~~'$argon2id$%'", True),
                      ("sessions", "session_expiry", "expires_at>created_at", True)}:
        raise ValueError("auth_schema_checks_invalid")


def verify_auth_connection(db):
    def require(value, code):
        if not value:
            raise ValueError(code)
    require(tuple(db.execute(text("SELECT current_database(), current_user, current_setting('transaction_read_only')")).one())
            == ("new_scm_dev", "new_scm_auth", "on"), "auth_database_identity_invalid")
    require(db.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
            == ["20261028_0014"], "alembic_revision_invalid")
    verify_auth_schema(db)
    require(db.execute(text("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='scm_auth' AND c.relname IN ('credentials','sessions','login_limits') AND c.relkind='r'
        AND has_table_privilege(c.oid,'SELECT') AND has_table_privilege(c.oid,'INSERT')
        AND has_table_privilege(c.oid,'UPDATE') AND has_table_privilege(c.oid,'DELETE')""")).scalar_one() == 3,
        "auth_schema_privileges_invalid")
    require(db.execute(text("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
        AND c.relkind IN ('r','p','v','m','f') AND (
            pg_has_role(current_user,c.relowner,'MEMBER') OR has_table_privilege(c.oid,'TRUNCATE,REFERENCES,TRIGGER')
            OR (NOT (n.nspname='scm_auth' AND c.relname IN ('credentials','sessions','login_limits'))
                AND (has_table_privilege(c.oid,'INSERT,UPDATE,DELETE') OR has_any_column_privilege(c.oid,'INSERT,UPDATE'))))
        """)).scalar_one() == 0, "auth_role_has_business_write_or_owner_privileges")
    require(not db.execute(text("SELECT has_column_privilege('public.users','password_hash','SELECT')")).scalar_one(),
            "auth_role_can_read_legacy_passwords")
    require(db.execute(text("""SELECT count(*) FROM pg_roles WHERE rolname=current_user
        AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)""")).scalar_one() == 0
        and db.execute(text("SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)")).scalar_one() == 0,
        "auth_role_has_elevated_privileges")
    require(not db.execute(text("SELECT has_schema_privilege('public','CREATE') OR has_schema_privilege('scm_auth','CREATE')")).scalar_one(),
            "auth_role_has_schema_create_privilege")
    require(not db.execute(text("SELECT has_database_privilege(current_database(),'CREATE')")).scalar_one(),
            "auth_role_has_database_create_privilege")
    require(db.execute(text("""SELECT count(*) FROM scm_auth.credentials c JOIN public.users u ON u.id=c.user_id
        WHERE c.enabled AND u.status='active' AND u.account_type='admin'
        AND EXISTS (SELECT FROM public.scm_user_grants g WHERE g.user_id=u.id AND g.grant_type='action' AND g.grant_name='system.access')
        AND EXISTS (SELECT FROM public.scm_user_grants g WHERE g.user_id=u.id AND g.grant_type='action' AND g.grant_name='admin.manage')""")).scalar_one() > 0,
        "standalone_admin_not_provisioned")
