"""Read-only NAS preparation checks. Never deploys application services.

Config-only checks use Python 3.8+ and the standard library only.
DB/API checks use Python 3.12+ dependencies, optionally in a disposable verifier.
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
from uuid import uuid4
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class Rejected(Exception):
    pass


def require(condition, code):
    if not condition:
        raise Rejected(code)


def command(args, environment=None, failure_code="command_failed_output_suppressed"):
    try:
        result = subprocess.run(args, env=environment, capture_output=True, timeout=30)
    except FileNotFoundError:
        raise Rejected("required_command_missing") from None
    except subprocess.TimeoutExpired:
        raise Rejected("command_timeout_output_suppressed") from None
    except OSError:
        raise Rejected("command_unavailable_output_suppressed") from None
    require(result.returncode == 0, failure_code)
    return result.stdout.decode("utf-8")


POSTGRES_STATE_FORMAT = '{{json .Id}} {{json .State.StartedAt}} {{json .RestartCount}} {{json .NetworkSettings.Networks}} {{json .HostConfig.PortBindings}}'
POSTGRES_NETWORK_FORMAT = '{{json .NetworkSettings.Networks}}'
POSTGRES_BINDING_FORMAT = '{{json .HostConfig.PortBindings}}'
BRIDGE_FORMAT = '{{json .IPAM.Config}}'
DOCKER_INFO_ARGS = ["info", "--format", "{{.ServerVersion}}"]


def verifier_run_args(name, image_id):
    require(re.fullmatch(r"scm-preflight-[0-9a-f]{32}", name), "verifier_name_invalid")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "verifier_image_invalid")
    return ["run", "--rm", "--name=" + name, "--pull=never", "--network=host", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--user=10001:10001",
            "--pids-limit=64", "--memory=256m", "--cpus=1", "--log-driver=none",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--interactive", "--entrypoint=python",
            image_id, "-I", "-B", "/srv/new-scm/deploy/preflight.py", "--isolated-worker"]


def trusted_executable(name):
    path = shutil.which(name)
    require(path, "docker_sudo_executable_missing")
    try:
        resolved = Path(path).resolve(strict=True)
        metadata = resolved.stat()
    except OSError:
        raise Rejected("docker_sudo_executable_unavailable") from None
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0
            and not metadata.st_mode & 0o022, "docker_sudo_executable_untrusted")
    return str(resolved)


def docker_argv(args, docker_sudo=False):
    """Only fixed daemon queries and the hardened disposable verifier may escalate."""
    allowed = args == DOCKER_INFO_ARGS or args in [
        ["inspect", "--format", value, "asset-postgres"]
        for value in (POSTGRES_STATE_FORMAT, POSTGRES_NETWORK_FORMAT, POSTGRES_BINDING_FORMAT)]
    allowed = allowed or args == ["network", "inspect", "--format", BRIDGE_FORMAT, "bridge"]
    if len(args) == 5 and args[:4] == ["image", "inspect", "--format", "{{.Id}}"]:
        allowed = isinstance(args[4], str) and bool(args[4]) and not args[4].startswith("-")
    if len(args) == 3 and args[:2] == ["rm", "--force"]:
        allowed = bool(re.fullmatch(r"scm-preflight-[0-9a-f]{32}", args[2]))
    if args and args[0] == "run" and len(args) >= 5:
        name = args[2][len("--name="):] if args[2].startswith("--name=") else ""
        allowed = args == verifier_run_args(name, args[-5])
    require(allowed, "docker_command_not_allowed")
    if docker_sudo:
        require(sys.platform == "linux", "docker_sudo_requires_linux")
        prefix = [trusted_executable("sudo"), "-n", "--", trusted_executable("docker")]
    else:
        prefix = ["docker"]
    # Probe this NAS, regardless of a shell's Docker context or remote endpoint.
    return prefix + ["--host=unix:///var/run/docker.sock"] + args


def docker_environment():
    return {key: value for key, value in os.environ.items()
            if not key.startswith(("DOCKER_", "COMPOSE_", "SCM_", "VITE_"))
            and key != "SUDO_ASKPASS"}


def docker_command(args, docker_sudo=False):
    return command(docker_argv(args, docker_sudo), docker_environment(),
                   "docker_sudo_command_failed" if docker_sudo else "docker_command_failed")


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
    try:
        config = json.loads(command(base + ["config", "--format", "json"], environment))
    except (ValueError, UnicodeError):
        raise Rejected("compose_json_invalid") from None
    return config


def validated_database_url(value):
    """No application/SQLAlchemy imports: this path must work on NAS Python 3.8."""
    try:
        url = urlsplit(value)
        port = url.port
        valid = (isinstance(value, str) and not any(c.isspace() for c in value)
                 and url.scheme == "postgresql+psycopg"
                 and unquote(url.username or "") == "new_scm_ro"
                 and url.path == "/new_scm_dev" and url.hostname
                 and url.netloc.count("@") == 1 and not url.query and not url.fragment
                 and (port is None or 0 < port < 65536))
    except (ValueError, TypeError, AttributeError):
        valid = False
    require(valid, "database_target_rejected")
    require(bool(url.password), "database_password_missing")
    return value


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
    # Compose versions emit a mapping or a list using ':' / '=' separators.
    # Match the entire value so extra entries and duplicates remain forbidden.
    require(backend["extra_hosts"] in ({"nas-host": "172.17.0.1"},
                                       ["nas-host:172.17.0.1"],
                                       ["nas-host=172.17.0.1"]),
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
    url = validated_database_url(env["SCM_DATABASE_URL"])
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


def protected_state(docker_sudo=False):
    require(shutil.which("ss") or shutil.which("netstat"), "ss_or_netstat_required")
    cli = ["ss", "-lntp"] if shutil.which("ss") else ["netstat", "-lntp"]
    listeners = command(cli).splitlines()
    protected = sorted(line for line in listeners if re.search(r":(80|8080|3010|8010)\s", line))
    require(all(any(re.search(rf":{port}\s", line) for line in listeners) for port in (3010, 8010)),
            "existing_asset_listeners_not_found")
    require(not any(re.search(r":8011\s", line) for line in listeners), "port_8011_in_use")
    # Only these fields are fetched. Full inspect would reveal container secrets.
    container = docker_command(["inspect", "--format", POSTGRES_STATE_FORMAT, "asset-postgres"], docker_sudo)
    return sha256(("\n".join(protected) + container).encode()).digest()


def host_docker_checks(docker_sudo=False):
    require(sys.platform == "linux", "nas_checks_require_linux")
    networks = json.loads(docker_command(["inspect", "--format", POSTGRES_NETWORK_FORMAT,
                                        "asset-postgres"], docker_sudo))
    require(set(networks) == {"bridge"}, "postgres_network_differs_from_confirmed_bridge")
    bridge = json.loads(docker_command(["network", "inspect", "--format", BRIDGE_FORMAT, "bridge"], docker_sudo))
    require(any(item.get("Gateway") == "172.17.0.1" for item in bridge), "docker_gateway_changed")
    binding = json.loads(docker_command(["inspect", "--format", POSTGRES_BINDING_FORMAT,
                                       "asset-postgres"], docker_sudo))
    require(binding.get("5432/tcp") == [{"HostIp": "127.0.0.1", "HostPort": "15432"}],
            "postgres_loopback_binding_changed")


def runtime_checks(raw_url):
    require(sys.version_info >= (3, 12), "runtime_checks_require_python_3_12")
    validated_database_url(raw_url)
    try:
        import httpx
        import psycopg
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import make_url
        from app.db.identity import load_identity
    except ImportError:
        raise Rejected("runtime_dependencies_missing_use_verifier_image") from None
    url = make_url(raw_url)
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


def script_digest():
    # Git checkouts may use CRLF on a build PC and LF on the NAS.
    return sha256(Path(__file__).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def isolated_runtime_checks(raw_url, image, docker_sudo=False):
    # Resolve an existing local image to an immutable ID. Never pull or build.
    require(bool(image) and not image.startswith("-"), "verifier_image_invalid")
    image_id = docker_command(["image", "inspect", "--format", "{{.Id}}", image], docker_sudo).strip()
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "verifier_image_invalid")
    payload = json.dumps({"database_url": raw_url, "script_sha256": script_digest()}).encode()
    name = "scm-preflight-" + uuid4().hex
    args = docker_argv(verifier_run_args(name, image_id), docker_sudo)
    needs_cleanup = True
    try:
        result = subprocess.run(args, input=payload, env=docker_environment(), capture_output=True, timeout=90)
        # Normal worker exits are already removed by --rm. CLI errors/timeouts
        # may leave a container, so only those paths need forced cleanup.
        needs_cleanup = not 0 <= result.returncode < 125
    except (OSError, subprocess.TimeoutExpired):
        raise Rejected("isolated_verifier_unavailable_output_suppressed") from None
    finally:
        # Killing a Docker CLI on timeout does not necessarily stop its container.
        # The unique name belongs only to this disposable verifier.
        if needs_cleanup:
            try:
                cleanup = subprocess.run(docker_argv(["rm", "--force", name], docker_sudo),
                                         env=docker_environment(), capture_output=True, timeout=10)
                require(cleanup.returncode == 0, "isolated_verifier_cleanup_failed")
            except (OSError, subprocess.TimeoutExpired):
                raise Rejected("isolated_verifier_cleanup_failed") from None
    # Only our fixed status codes may reach the terminal, never raw Docker output.
    safe_codes = {"verifier_script_mismatch", "runtime_checks_require_python_3_12",
                  "runtime_dependencies_missing_use_verifier_image", "database_runtime_probe_failed",
                  "database_identity_or_readonly_invalid", "expected_54_tables", "alembic_revision_invalid",
                  "readonly_role_has_write_or_owner_privileges", "readonly_role_has_elevated_privileges",
                  "expected_identity_mapping_or_grant_missing", "expected_scm_admin_missing",
                  "identity_openapi_unreachable", "running_identity_handoff_routes_missing",
                  "scm_user_data_changed_during_checks"}
    output = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        if output in {"FAIL " + code for code in safe_codes}:
            raise Rejected(output[5:])
        raise Rejected("docker_sudo_or_verifier_failed" if docker_sudo
                       else "isolated_verifier_failed_output_suppressed")
    require(output == "PASS isolated_db_api_checks", "isolated_verifier_response_invalid")


def isolated_worker():
    try:
        payload = json.load(sys.stdin)
        require(payload["script_sha256"] == script_digest(),
                "verifier_script_mismatch")
        runtime_checks(payload["database_url"])
        print("PASS isolated_db_api_checks")
        return 0
    except Rejected as exc:
        print("FAIL " + str(exc))
    except Exception:
        print("FAIL database_runtime_probe_failed")
    return 1


def host_checks(env, url, isolated_image=None, docker_sudo=False):
    require(sys.platform == "linux", "nas_checks_require_linux")
    if docker_sudo:
        # Noninteractive: authenticate with sudo -v in the caller's terminal first.
        docker_command(DOCKER_INFO_ARGS, docker_sudo)
    baseline = protected_state(docker_sudo)
    try:
        host_docker_checks(docker_sudo)
        if isolated_image:
            isolated_runtime_checks(url, isolated_image, docker_sudo)
        else:
            runtime_checks(url)
    finally:
        require(protected_state(docker_sudo) == baseline, "protected_listeners_or_postgres_state_changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-only", action="store_true", help="Skip NAS/DB/API probes")
    parser.add_argument("--compose-executable", help="Optional standalone Compose binary")
    parser.add_argument("--env-file", type=Path, help="Explicit alternative env file; never modified")
    parser.add_argument("--docker-sudo", action="store_true",
                        help="Use sudo -n only for allowed Docker daemon operations; authenticate with sudo -v first")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--isolated-image", help="Existing trusted verifier image; runs a disposable DB/API probe")
    modes.add_argument("--isolated-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.isolated_worker:
        return isolated_worker()
    try:
        require(not (args.config_only and args.isolated_image), "config_only_does_not_start_verifier")
        config = compose_config(args.compose_executable, args.env_file)
        env, url = validate_config(config)
        print("PASS compose/env/network/port policy (no values printed)")
        if not args.config_only:
            host_checks(env, url, args.isolated_image, args.docker_sudo)
            print("PASS NAS host DB/readonly/schema/mapping/API/protected-state checks")
        print("PENDING container-to-host routing, Unix volume, live Nginx, shared-key equality, browser SSO")
        print("NO application services built/started; NO deployment approval implied")
        return 0
    except Rejected as exc:
        print("FAIL " + str(exc))  # Only fixed error identifiers reach this branch.
    except (KeyError, TypeError, AttributeError):
        print("FAIL configuration_structure_invalid")
    except Exception:
        print("FAIL preflight_unavailable_details_suppressed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
