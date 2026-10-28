"""Fixture-only backup/restore helpers; never accepts a NAS or existing DB target."""
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from sqlalchemy import create_engine, text

DOCKER = ["/usr/bin/docker", "--host=unix:///var/run/docker.sock"]


def fixture_container():
    name = os.environ.get("SCM_TEST_PG_CONTAINER", "")
    if not re.fullmatch(r"scm-i-test-[0-9a-f]{32}", name):
        raise RuntimeError("local_fixture_container_required")
    fmt = '{"network":{{json .HostConfig.NetworkMode}},"ports":{{json .HostConfig.PortBindings}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}}}'
    result = subprocess.run(DOCKER + ["inspect", "--format", fmt, name], capture_output=True, timeout=10)
    if result.returncode:
        raise RuntimeError("local_fixture_inspection_failed")
    state = json.loads(result.stdout)
    wanted = str(Path(os.environ["SCM_TEST_PG_SOCKET"]).resolve(strict=True))
    if (state["network"] != "none" or state["ports"]
            or state["labels"].get("new-scm.test-purpose") != "4-2i"
            or not any(item["Source"] == wanted and item["Destination"] == "/var/run/postgresql"
                       for item in state["mounts"])):
        raise RuntimeError("local_fixture_isolation_invalid")
    return name


def backup():
    result = subprocess.run(DOCKER + ["exec", fixture_container(), "pg_dump", "-U", "postgres",
        "--dbname=new_scm_dev", "--format=custom"], capture_output=True, timeout=30)
    if result.returncode or not result.stdout.startswith(b"PGDMP"):
        raise RuntimeError("fixture_backup_failed_output_suppressed")
    return result.stdout


def restore(owner, archive):
    # Always a NEW database, inside the same verified disposable local cluster.
    fixture_container()
    name = "scm_restore_" + uuid4().hex
    with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as db:
        db.execute(text('CREATE DATABASE "' + name + '"'))
    result = subprocess.run(DOCKER + ["exec", "--interactive", fixture_container(), "pg_restore",
        "-U", "postgres", "--dbname=" + name, "--exit-on-error", "--single-transaction"],
        input=archive, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError("fixture_restore_failed_output_suppressed")
    return create_engine(owner.url.set(database=name), hide_parameters=True)


def fingerprint(db, ignore_revision_data=False, include_auth=True, exclude_auth_role=False):
    # Only synthetic fixture tables are accepted; values stay in the DB as digests.
    database = db.execute(text("SELECT current_database()")).scalar_one()
    if database != "new_scm_dev" and not re.fullmatch(r"scm_restore_[0-9a-f]{32}", database):
        raise RuntimeError("fixture_database_target_rejected")
    def selected(sql):
        return text(sql.replace("('public','scm_auth')", "('public')") if not include_auth else sql)
    tables = db.execute(selected("SELECT schemaname,tablename,tableowner FROM pg_tables "
        "WHERE schemaname IN ('public','scm_auth') ORDER BY 1,2")).all()
    rows = {}
    quote = db.dialect.identifier_preparer.quote
    for schema, table, _owner in tables:
        if ignore_revision_data and (schema, table) == ("public", "alembic_version"):
            continue
        target = quote(schema) + "." + quote(table)
        rows[(schema, table)] = tuple(db.execute(text(
            "SELECT count(*),md5(coalesce(string_agg(row_to_json(t)::text,chr(10) "
            "ORDER BY row_to_json(t)::text),'')) FROM " + target + " t")).one())
    queries = {
        "columns": "SELECT table_schema,table_name,column_name,data_type,udt_name,character_maximum_length,is_nullable,column_default "
                   "FROM information_schema.columns WHERE table_schema IN ('public','scm_auth') ORDER BY 1,2,ordinal_position",
        "constraints": "SELECT n.nspname,c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid),k.convalidated,k.condeferrable "
                       "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "WHERE n.nspname IN ('public','scm_auth') ORDER BY 1,2,3",
        "indexes": "SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes WHERE schemaname IN ('public','scm_auth') ORDER BY 1,2,3",
        "table_acl": "SELECT grantor,grantee,table_schema,table_name,privilege_type,is_grantable FROM information_schema.table_privileges "
                     "WHERE table_schema IN ('public','scm_auth') ORDER BY 1,2,3,4,5",
        "column_acl": "SELECT grantor,grantee,table_schema,table_name,column_name,privilege_type,is_grantable "
                      "FROM information_schema.column_privileges WHERE table_schema IN ('public','scm_auth') ORDER BY 1,2,3,4,5,6",
        "schema_acl": "SELECT n.nspname,pg_get_userbyid(n.nspowner),coalesce(r.rolname,'PUBLIC'),a.privilege_type,a.is_grantable "
                      "FROM pg_namespace n LEFT JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a ON true "
                      "LEFT JOIN pg_roles r ON r.oid=a.grantee WHERE n.nspname IN ('public','scm_auth') ORDER BY 1,2,3,4,5",
    }
    result = {name: [tuple(row) for row in db.execute(selected(query)).all()] for name, query in queries.items()}
    # PostgreSQL reparses this legacy varchar-array cast into per-element text
    # casts during pg_restore. Canonicalize only this known enum CHECK; preserve
    # its column, operator and exact allowed values. Other constraints stay exact.
    normalized = []
    for row in result["constraints"]:
        if row[:4] == ("public", "scm_user_grants", "ck_scm_grant_type", "c"):
            row = row[:4] + (re.sub(r"\s+|[()]|::text(?:\[\])?|::character varying", "", row[4]),) + row[5:]
        normalized.append(row)
    result["constraints"] = normalized
    if exclude_auth_role:
        # 0014 intentionally adds only this role's SELECT/USAGE grants on public.
        for name, position in (("table_acl", 1), ("column_acl", 1), ("schema_acl", 2)):
            result[name] = [row for row in result[name] if row[position] != "new_scm_auth"]
    result.update(tables=[tuple(row) for row in tables], rows=rows)
    result["sequences"] = {}
    for schema, sequence in db.execute(selected("SELECT schemaname,sequencename FROM pg_sequences "
            "WHERE schemaname IN ('public','scm_auth') ORDER BY 1,2")).all():
        result["sequences"][(schema, sequence)] = tuple(db.execute(text(
            "SELECT last_value,is_called FROM " + quote(schema) + "." + quote(sequence))).one())
    return result
