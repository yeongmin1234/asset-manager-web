"""Read-only NAS preparation checks. Never builds, starts, or changes services.

Run with a Python environment containing new-scm/backend/requirements.txt.
Compose output and subprocess errors are captured because they may hold secrets.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class Rejected(Exception):
    pass


def require(condition, code):
    if not condition:
        raise Rejected(code)


def command(args, environment=None):
    result = subprocess.run(args, env=environment, capture_output=True, timeout=30)
    require(result.returncode == 0, "command_failed_output_suppressed")
    return result.stdout.decode("utf-8")


def compose_config(executable=None, env_file=None):
    path = Path(env_file) if env_file else ROOT / ".env"
    require(path.is_file() and not path.is_symlink(), "env_file_missing_or_symlink")
    if os.name == "posix":
        require(stat.S_IMODE(path.stat().st_mode) == 0o600, "env_mode_must_be_600")
        require(path.stat().st_uid == os.geteuid(), "env_owner_must_be_current_user")
    # Explicit env file; prevent a caller's shell from overriding deployment values.
    environment = {k: v for k, v in os.environ.items()
                   if not k.startswith(("SCM_", "VITE_", "COMPOSE_"))}
    environment["SCM_ENV_FILE"] = str(path.resolve())
    cli = [executable] if executable else ["docker", "compose"]
    version = command(cli + ["version", "--short"], environment)
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", version)
    require(match and tuple(map(int, match.groups())) >= (2, 20, 1), "compose_2_20_1_required")
    base = cli + ["--project-name", "new-scm", "--env-file", str(path),
                  "-f", str(ROOT / "deploy" / "compose.yaml")]
    config = json.loads(command(base + ["config", "--format", "json"], environment))
    return config


def browser_origin(value):
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        raise Rejected("browser_origin_invalid") from None
    require(url.scheme in {"http", "https"} and url.hostname
            and not (url.username or url.password or url.path or url.query or url.fragment)
            and port not in {5173, 5174}, "browser_origin_invalid_or_development_port")
    require(url.scheme == "https" or url.hostname in {"127.0.0.1", "localhost"},
            "browser_http_requires_local_tunnel")
    return url


def validate_config(config):
    from app.db.database import _validated_url
    services = config["services"]
    require(set(services) == {"db-relay", "backend", "frontend"}, "unexpected_services")
    backend, frontend, relay = (services[name] for name in ("backend", "frontend", "db-relay"))
    require(set(backend["networks"]) == {"scm_internal"}
            and set(frontend["networks"]) == {"scm_internal"}, "scm_network_invalid")
    require(not backend.get("ports") and not relay.get("ports")
            and relay["network_mode"] == "host", "backend_or_relay_port_exposed")
    require(not relay.get("environment") and not relay.get("privileged")
            and relay.get("read_only") and relay.get("user", "10001:10001") == "10001:10001",
            "relay_isolation_invalid")
    ports = frontend["ports"]
    require(len(ports) == 1 and ports[0]["host_ip"] == "127.0.0.1"
            and str(ports[0]["published"]) == "8011" and ports[0]["target"] == 80,
            "frontend_must_bind_loopback_8011")
    require(frontend["build"]["args"]["VITE_SCM_API_BASE_URL"] == "/api/v1",
            "frontend_api_base_invalid")
    require(backend["extra_hosts"] in ({"nas-host": "172.17.0.1"}, ["nas-host:172.17.0.1"]),
            "identity_gateway_invalid")
    env = backend["environment"]
    required = ("SCM_ENV", "SCM_DATABASE_URL", "SCM_DIAGNOSTICS_KEY", "SCM_CORS_ORIGINS",
                "SCM_BIND_HOST", "SCM_HTTP_PORT", "VITE_SCM_API_BASE_URL",
                "SCM_IDENTITY_BASE_URL", "SCM_HANDOFF_KEY", "SCM_HANDOFF_ORIGIN", "SCM_FRONTEND_ORIGIN")
    require(all(key in env for key in required), "required_env_keys_missing")
    require(env["SCM_ENV"] in {"development", "production"}, "environment_invalid")
    require(env["SCM_BIND_HOST"] == "127.0.0.1" and env["SCM_HTTP_PORT"] == "8011",
            "env_bind_must_match_loopback_8011")
    require(env["VITE_SCM_API_BASE_URL"] == "/api/v1", "env_api_base_invalid")
    require(len(env["SCM_HANDOFF_KEY"] or "") >= 32
            and len(env["SCM_DIAGNOSTICS_KEY"] or "") >= 32,
            "handoff_and_diagnostics_keys_require_32_characters")
    require(env["SCM_HANDOFF_KEY"] != env["SCM_DIAGNOSTICS_KEY"], "keys_must_be_distinct")
    require(env["SCM_IDENTITY_BASE_URL"] == "http://nas-host:8010"
            and env["SCM_DATABASE_SOCKET_DIR"] == "/srv/new-scm/db-socket", "internal_route_invalid")
    url = _validated_url(env["SCM_DATABASE_URL"])
    require(bool(url.password), "database_password_missing")
    source = browser_origin(env["SCM_HANDOFF_ORIGIN"] or "")
    destination = browser_origin(env["SCM_FRONTEND_ORIGIN"] or "")
    # SameSite=Lax cookies cannot support a cross-site fetch handoff.
    require((source.scheme, source.hostname) == (destination.scheme, destination.hostname),
            "handoff_requires_same_site_browser_origins")
    if env["SCM_ENV"] == "production":
        require(source.scheme == destination.scheme == "https", "production_requires_https")
    else:
        require(destination.scheme == "http" and destination.hostname in {"127.0.0.1", "localhost"}
                and destination.port == 8011, "initial_validation_requires_local_tunnel_8011")
    allowed = {env["SCM_HANDOFF_ORIGIN"], env["SCM_FRONTEND_ORIGIN"]}
    for origin in (env["SCM_CORS_ORIGINS"] or "").split(","):
        if origin.strip():
            browser_origin(origin.strip())
            require(origin.strip() in allowed, "cors_origin_not_confirmed")
    return env, url


def protected_state():
    require(shutil.which("ss") or shutil.which("netstat"), "ss_or_netstat_required")
    cli = ["ss", "-lntp"] if shutil.which("ss") else ["netstat", "-lntp"]
    listeners = command(cli).splitlines()
    protected = sorted(line for line in listeners if re.search(r":(80|8080|3010|8010)\s", line))
    require(all(any(re.search(rf":{port}\s", line) for line in listeners) for port in (3010, 8010)),
            "existing_asset_listeners_not_found")
    require(not any(re.search(r":8011\s", line) for line in listeners), "port_8011_in_use")
    # Only these fields are fetched. Full inspect would reveal container secrets.
    template = '{{json .Id}} {{json .State.StartedAt}} {{json .RestartCount}} {{json .NetworkSettings.Networks}} {{json .HostConfig.PortBindings}}'
    container = command(["docker", "inspect", "--format", template, "asset-postgres"])
    return sha256(("\n".join(protected) + container).encode()).digest()


def host_checks(env, url):
    import httpx
    from sqlalchemy import create_engine, text
    require(sys.platform == "linux", "nas_checks_require_linux")
    baseline = protected_state()
    networks = json.loads(command(["docker", "inspect", "--format",
                                  "{{json .NetworkSettings.Networks}}", "asset-postgres"]))
    require(set(networks) == {"bridge"}, "postgres_network_differs_from_confirmed_bridge")
    bridge = json.loads(command(["docker", "network", "inspect", "--format",
                                "{{json .IPAM.Config}}", "bridge"]))
    require(any(item.get("Gateway") == "172.17.0.1" for item in bridge), "docker_gateway_changed")
    binding = json.loads(command(["docker", "inspect", "--format",
                                 "{{json .HostConfig.PortBindings}}", "asset-postgres"]))
    require(binding.get("5432/tcp") == [{"HostIp": "127.0.0.1", "HostPort": "15432"}],
            "postgres_loopback_binding_changed")
    # The NAS preflight probes the same host loopback target used by db-relay.
    engine = create_engine(url.set(host="127.0.0.1", port=15432), pool_size=1, max_overflow=0,
                           connect_args={"connect_timeout": 3,
                                         "options": "-c default_transaction_read_only=on -c statement_timeout=3000"})
    try:
        with engine.connect() as db:
            identity = db.execute(text("SELECT current_database(), current_user, current_setting('transaction_read_only')")).one()
            require(tuple(identity) == ("new_scm_dev", "new_scm_ro", "on"), "database_identity_or_readonly_invalid")
            require(db.execute(text("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p')")).scalar_one() == 54,
                    "expected_54_tables")
            require(db.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all() == ["20261027_0013"],
                    "alembic_revision_invalid")
            writable = db.execute(text("""
                SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') AND (
                    has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE') OR
                    has_any_column_privilege(c.oid, 'INSERT,UPDATE') OR
                    pg_has_role(current_user, c.relowner, 'MEMBER'))
            """)).scalar_one()
            require(writable == 0, "readonly_role_has_write_or_owner_privileges")
            elevated = db.execute(text("""
                SELECT count(*) FROM pg_roles WHERE pg_has_role(current_user, oid, 'MEMBER')
                AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
            """)).scalar_one()
            require(elevated == 0 and not db.execute(text("SELECT has_schema_privilege('public', 'CREATE')")).scalar_one(),
                    "readonly_role_has_elevated_privileges")
            from app.db.identity import load_identity
            mapped = load_identity(db, "asset-manager", "3")
            require(mapped is not None and mapped[0].id == 1
                    and ("action", "system.access") in mapped[1], "expected_identity_mapping_or_grant_missing")
            require(db.execute(text("SELECT username FROM public.users WHERE id=1")).scalar_one() == "admin",
                    "expected_scm_admin_missing")
            snapshot_sql = text("SELECT count(*), md5(coalesce(string_agg(md5(row_to_json(u)::text), '' ORDER BY u.id), '')) FROM public.users u")
            before = tuple(db.execute(snapshot_sql).one())
            # Only GET requests. No code issuance, exchange, session, or DB writes.
            with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
                for host in ("127.0.0.1", "172.17.0.1"):
                    response = client.get(f"http://{host}:8010/openapi.json")
                    require(response.status_code == 200, "identity_openapi_unreachable")
                    paths = response.json().get("paths", {})
                    require(all("post" in paths.get(path, {}) for path in
                                ("/auth/scm-handoff/issue", "/auth/scm-handoff/exchange")),
                            "running_identity_handoff_routes_missing")
            require(tuple(db.execute(snapshot_sql).one()) == before, "scm_user_data_changed_during_checks")
            db.rollback()
    finally:
        engine.dispose()
    require(protected_state() == baseline, "protected_listeners_or_postgres_state_changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-only", action="store_true", help="Skip NAS/DB/API probes")
    parser.add_argument("--compose-executable", help="Optional standalone Compose binary")
    parser.add_argument("--env-file", type=Path, help="Explicit alternative env file; never modified")
    args = parser.parse_args()
    try:
        config = compose_config(args.compose_executable, args.env_file)
        env, url = validate_config(config)
        print("PASS compose/env/network/port policy (no values printed)")
        if not args.config_only:
            host_checks(env, url)
            print("PASS NAS host DB/readonly/schema/mapping/API/protected-state checks")
        print("PENDING container-to-host routing, Unix volume, live Nginx, shared-key equality, browser SSO")
        print("NO containers built/started; NO deployment approval implied")
        return 0
    except Rejected as exc:
        print("FAIL " + str(exc))  # Only fixed error identifiers reach this branch.
    except Exception:
        print("FAIL preflight_unavailable_details_suppressed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
