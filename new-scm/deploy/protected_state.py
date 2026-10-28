"""Python 3.8+ read-only NAS snapshots. Never starts/stops/executes containers."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
import urllib.error
import urllib.request

import preflight

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_FORMAT = ('{"id":{{json .Id}},"image":{{json .Image}},'
                   '"running":{{json .State.Running}},"paused":{{json .State.Paused}},'
                   '"restarting":{{json .State.Restarting}},"oom":{{json .State.OOMKilled}},'
                   '"started":{{json .State.StartedAt}},"finished":{{json .State.FinishedAt}},'
                   '"restarts":{{json .RestartCount}},"networks":{{json .NetworkSettings.Networks}},'
                   '"ports":{{json .HostConfig.PortBindings}}}')


def digest(value):
    return sha256(value).hexdigest()


def docker_read(args, use_sudo):
    allowed = (["inspect", "--format", POSTGRES_FORMAT, "asset-postgres"],
               ["info", "--format", "{{.ServerVersion}}"], ["ps", "--format", "{{.Ports}}"])
    preflight.require(args in allowed, "protected_query_not_allowed")
    prefix = ([preflight.trusted_executable("sudo"), "-n", "--", preflight.trusted_executable("docker")]
              if use_sudo else ["docker"])
    return preflight.command(prefix + ["--host=unix:///var/run/docker.sock"] + args,
                             preflight.docker_environment(), "protected_docker_query_failed")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_status(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(url, timeout=3) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def scm_json_ok(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=3) as response:
        value = json.loads(response.read(65536))
        return (response.status == 200 and isinstance(value, dict) and value.get("ok") is True
                and isinstance(value.get("data"), dict) and value["data"].get("service") == "new-scm")


def verify_test_config(env_file=None, image_file=None, compose_executable=None, phase="post-migration"):
    env_file, image_file = Path(env_file or ROOT / ".env"), Path(image_file or ROOT / ".nas-test-images.env")
    preflight.require(image_file.is_file() and not image_file.is_symlink(), "nas_test_image_file_missing")
    if os.name == "posix":
        metadata = image_file.stat()
        preflight.require(metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) == 0o600,
                          "nas_test_image_file_owner_or_mode_invalid")
    images = {}
    for line in image_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        preflight.require(separator and key in {"SCM_TEST_BACKEND_IMAGE", "SCM_TEST_FRONTEND_IMAGE"}
                          and key not in images and re.fullmatch(r"sha256:[0-9a-f]{64}", value),
                          "nas_test_image_file_invalid")
        images[key] = value
    preflight.require(len(images) == 2, "nas_test_image_file_invalid")
    base = preflight.compose_config(compose_executable, env_file)
    env, _url = preflight.validate_config(base, phase)
    preflight.require(env["SCM_ENV"] == "development", "nas_test_requires_development_env")
    environment = preflight.docker_environment()
    environment.update(images)
    environment["SCM_ENV_FILE"] = str(env_file.resolve())
    cli = [compose_executable] if compose_executable else ["docker", "compose"]
    resolved = json.loads(preflight.command(cli + ["--project-name", "new-scm-4-2h", "--env-file", str(env_file),
        "--env-file", str(image_file), "-f", str(ROOT / "deploy/compose.nas-test.yaml"),
        "config", "--format", "json"], environment))
    services = resolved["services"]
    preflight.require(resolved["name"] == "new-scm-4-2h" and set(services) == {"frontend", "backend", "db-relay"},
                      "nas_test_scope_invalid")
    for name, memory, uid in (("db-relay", 64, "10001:10001"), ("backend", 256, "10001:10001"),
                              ("frontend", 128, "101:101")):
        service = services[name]
        expected_image = images["SCM_TEST_FRONTEND_IMAGE" if name == "frontend" else "SCM_TEST_BACKEND_IMAGE"]
        memory_value = service.get("mem_limit")
        preflight.require(type(memory_value) in (int, str) and re.fullmatch(r"[0-9]+", str(memory_value)),
                          "nas_test_service_policy_invalid")
        preflight.require(service["image"] == expected_image and service["user"] == uid
                          and service["read_only"] and int(memory_value) == memory * 1024 * 1024
                          and service["restart"] == "no" and service["pull_policy"] == "never"
                          and service["logging"]["driver"] == "none" and service["cap_drop"] == ["ALL"]
                          and "no-new-privileges:true" in service["security_opt"]
                          and not any(service.get(key) for key in
                                      ("privileged", "build", "container_name", "devices", "cap_add", "cpus", "pids_limit")),
                          "nas_test_service_policy_invalid")
    backend, frontend, relay = services["backend"], services["frontend"], services["db-relay"]
    preflight.require(backend["environment"] == base["services"]["backend"]["environment"]
                      and not backend.get("extra_hosts")
                      and not frontend.get("environment") and not backend.get("ports") and not relay.get("ports")
                      and relay["network_mode"] == "host" and not relay.get("environment"), "nas_test_route_invalid")
    ports = frontend["ports"]
    preflight.require(len(ports) == 1 and ports[0]["host_ip"] == "127.0.0.1"
                      and str(ports[0]["published"]) == "8011" and ports[0]["target"] == 8081,
                      "nas_test_port_invalid")
    for name, readonly in (("backend", True), ("db-relay", False)):
        mounts = services[name]["volumes"]
        preflight.require(len(mounts) == 1 and mounts[0]["type"] == "volume"
                          and mounts[0]["source"] == "scm_db_socket"
                          and mounts[0]["target"] == "/srv/new-scm/db-socket"
                          and mounts[0].get("read_only", False) is readonly, "nas_test_volume_invalid")
    preflight.require(not frontend.get("volumes") and set(backend["networks"]) == {"scm_internal"}
                      and set(frontend["networks"]) == {"scm_internal"}, "nas_test_network_invalid")
    for collection, key in (("volumes", "scm_db_socket"), ("networks", "scm_internal")):
        preflight.require(set(resolved[collection]) == {key}, "nas_test_resource_scope_invalid")
        resource = resolved[collection][key]
        preflight.require(resource["name"] == "new-scm-4-2h_" + key and not resource.get("external"),
                          "nas_test_resource_scope_invalid")


def collect(use_sudo=False, require_free_port=False, env_file=None):
    preflight.require(sys.platform == "linux", "protected_snapshot_requires_linux")
    env = Path(env_file) if env_file else ROOT / ".env"
    preflight.require(env.is_file() and not env.is_symlink(), "env_file_missing_or_symlink")
    metadata = env.stat()
    preflight.require(stat.S_IMODE(metadata.st_mode) == 0o600, "env_mode_must_be_600")
    preflight.require(metadata.st_uid == os.geteuid(), "env_owner_must_be_current_user")
    images = ROOT / ".nas-test-images.env"
    preflight.require(images.is_file() and not images.is_symlink(), "nas_test_image_file_missing")
    image_metadata = images.stat()
    preflight.require(image_metadata.st_uid == os.geteuid() and stat.S_IMODE(image_metadata.st_mode) == 0o600,
                      "nas_test_image_file_owner_or_mode_invalid")
    cli = ["ss", "-lntp"] if preflight.shutil.which("ss") else ["netstat", "-lntp"]
    listeners = preflight.command(cli).splitlines()
    protected = sorted(line for line in listeners if re.search(r":(80|8080|3010|8010|15432)\s", line))
    preflight.require(all(any(re.search(r":%d\s" % port, line) for line in protected)
                          for port in (15432,)), "protected_listener_missing")
    postgres = json.loads(docker_read(["inspect", "--format", POSTGRES_FORMAT, "asset-postgres"], use_sudo))
    preflight.require(postgres.get("running") is True and not any(postgres.get(key)
                      for key in ("paused", "restarting", "oom")), "protected_postgres_not_healthy")
    version = docker_read(["info", "--format", "{{.ServerVersion}}"], use_sudo).strip()
    match = re.match(r"(\d+)\.", version)
    preflight.require(match is not None, "protected_docker_version_invalid")
    if int(match.group(1)) < 28:
        print("WARN docker_loopback_l2_protection_unverified")
    if require_free_port:
        publications = docker_read(["ps", "--format", "{{.Ports}}"], use_sudo)
        preflight.require(not any(re.search(r":8011\s", line) for line in listeners)
                          and ":8011->" not in publications, "nas_test_port_8011_in_use")
    statuses = []  # Asset-manager HTTP availability is not an SCM prerequisite.
    return {"schema": 1, "listeners": digest("\n".join(protected).encode()),
            "postgres": digest(json.dumps(postgres, sort_keys=True).encode()),
            "docker_version": version, "http": statuses,
            "env": digest(env.read_bytes()), "env_owner": metadata.st_uid, "env_mode": 0o600,
            "test_images": digest(images.read_bytes()),
            "test_compose": digest((ROOT / "deploy/compose.nas-test.yaml").read_bytes())}


def snapshot_path(value):
    preflight.require(not (ROOT / "runtime").is_symlink() and not (ROOT / "runtime/4-2h").is_symlink(),
                      "protected_snapshot_path_invalid")
    directory = (ROOT / "runtime/4-2h").resolve()
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    preflight.require(not path.is_symlink() and path.resolve().parent == directory
                      and path.suffix == ".json", "protected_snapshot_path_invalid")
    return path


def main(argv=None):
    parser = preflight.SafeArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check-config", "check-http", "capture", "compare"))
    parser.add_argument("--file", default="runtime/4-2h/protected-before.json")
    parser.add_argument("--docker-sudo", action="store_true")
    parser.add_argument("--compose-executable")
    parser.add_argument("--phase", choices=preflight.PHASES, default="post-migration")
    parser.add_argument("--env-file", type=Path, help="Separate standalone env file; never modified")
    args = parser.parse_args(argv)
    try:
        if args.action == "check-http":
            try:
                healthy = (http_status("http://127.0.0.1:8011/") == 200
                           and scm_json_ok("http://127.0.0.1:8011/health")
                           and scm_json_ok("http://127.0.0.1:8011/api/v1/system/status"))
            except Exception:
                raise preflight.Rejected("nas_test_http_unavailable") from None
            preflight.require(healthy, "nas_test_http_not_healthy")
            print("PASS nas_test_http")
            return 0
        if args.action == "check-config":
            verify_test_config(env_file=args.env_file, compose_executable=args.compose_executable, phase=args.phase)
            print("PASS nas_test_config_only_no_containers_started")
            return 0
        path = snapshot_path(args.file)
        if args.action == "capture":
            state = collect(args.docker_sudo, require_free_port=True, env_file=args.env_file)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            metadata = path.parent.stat()
            preflight.require(metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) == 0o700,
                              "protected_snapshot_directory_invalid")
            with open(path, "x", encoding="utf-8", opener=lambda name, flags: os.open(name, flags, 0o600)) as handle:
                json.dump(state, handle, sort_keys=True)
        else:
            metadata = path.stat()
            preflight.require(metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) == 0o600,
                              "protected_snapshot_owner_or_mode_invalid")
            previous = json.loads(path.read_text(encoding="utf-8"))
            preflight.require(previous == collect(args.docker_sudo, env_file=args.env_file), "protected_state_changed")
        print("PASS protected_" + args.action)
        return 0
    except preflight.Rejected as exc:
        print("FAIL " + str(exc))
    except FileExistsError:
        print("FAIL protected_snapshot_already_exists")
    except Exception:
        print("FAIL protected_snapshot_unavailable")
    return 1


if __name__ == "__main__":
    sys.exit(main())
