import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("scm_preflight", Path(__file__).with_name("preflight.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def config():
    return {"services": {
        "db-relay": {"network_mode": "host", "read_only": True},
        "frontend": {"networks": {"scm_internal": {}},
                     "ports": [{"host_ip": "127.0.0.1", "published": "8011", "target": 80}],
                     "build": {"args": {"VITE_SCM_API_BASE_URL": "/api/v1"}}},
        "backend": {"networks": {"scm_internal": {}}, "extra_hosts": {"nas-host": "172.17.0.1"},
                    "environment": {
                        "SCM_ENV": "development",
                        "SCM_DATABASE_URL": "postgresql+psycopg://new_scm_ro:test-only@localhost:15432/new_scm_dev",
                        "SCM_DATABASE_SOCKET_DIR": "/srv/new-scm/db-socket",
                        "SCM_DIAGNOSTICS_KEY": "test-diagnostics-" * 3, "SCM_CORS_ORIGINS": "",
                        "SCM_BIND_HOST": "127.0.0.1", "SCM_HTTP_PORT": "8011",
                        "VITE_SCM_API_BASE_URL": "/api/v1", "SCM_IDENTITY_BASE_URL": "http://nas-host:8010",
                        "SCM_HANDOFF_KEY": "test-handoff-" * 4,
                        "SCM_HANDOFF_ORIGIN": "http://127.0.0.1:3010",
                        "SCM_FRONTEND_ORIGIN": "http://127.0.0.1:8011"}},
    }}


class PreflightTests(unittest.TestCase):
    def test_local_tunnel_configuration_passes(self):
        preflight.validate_config(config())

    def test_identity_gateway_accepts_compose_output_formats(self):
        for extra_hosts in ({"nas-host": "172.17.0.1"},
                            ["nas-host:172.17.0.1"],
                            ["nas-host=172.17.0.1"]):
            with self.subTest(extra_hosts=extra_hosts):
                candidate = config()
                candidate["services"]["backend"]["extra_hosts"] = extra_hosts
                preflight.validate_config(candidate)

    def test_identity_gateway_rejects_wrong_missing_and_duplicate_mappings(self):
        rejected = (
            None, {}, [], "nas-host=172.17.0.1",
            {"other-host": "172.17.0.1"},
            {"nas-host": "172.17.0.2"},
            {"nas-host": "host-gateway"},
            {"nas-host": ["172.17.0.1"]},
            {"nas-host": "172.17.0.1", "other-host": "172.17.0.1"},
            ["nas-host:172.17.0.1", "nas-host:172.17.0.1"],
            ["nas-host=172.17.0.1", "nas-host=172.17.0.1"],
            ["nas-host:172.17.0.1", "nas-host=172.17.0.1"],
            ["nas-host=172.17.0.1", "nas-host=172.17.0.2"],
            ["nas-host=172.17.0.1", "other-host=172.17.0.1"],
            ["nas-host=172.17.0.1 "],
            [{"nas-host": "172.17.0.1"}],
        )
        for separator in (":", "="):
            for host, ip in (("other-host", "172.17.0.1"),
                             ("NAS-HOST", "172.17.0.1"),
                             ("nas-host", "172.17.0.2"),
                             ("nas-host", "127.0.0.1"),
                             ("nas-host", "host-gateway"),
                             ("nas-host", "")):
                rejected += ([f"{host}{separator}{ip}"],)
        for extra_hosts in rejected:
            with self.subTest(extra_hosts=extra_hosts):
                candidate = config()
                candidate["services"]["backend"]["extra_hosts"] = extra_hosts
                with self.assertRaisesRegex(preflight.Rejected, "^identity_gateway_invalid$"):
                    preflight.validate_config(candidate)

    def test_policy_rejects_public_port_wrong_role_origins_and_missing_secrets(self):
        for field, value in (("SCM_BIND_HOST", "0.0.0.0"), ("SCM_HTTP_PORT", "3010"),
                             ("SCM_HANDOFF_ORIGIN", "http://127.0.0.1:5173"),
                             ("SCM_HANDOFF_ORIGIN", "http://localhost:3010"),
                             ("SCM_FRONTEND_ORIGIN", "http://nas.example:8011"),
                             ("SCM_HANDOFF_KEY", ""), ("SCM_CORS_ORIGINS", "*")):
            candidate = config()
            candidate["services"]["backend"]["environment"][field] = value
            with self.subTest(field=field), self.assertRaises(preflight.Rejected):
                preflight.validate_config(candidate)
        for service in ("backend", "db-relay"):
            candidate = config()
            candidate["services"][service]["ports"] = [{"published": "8012"}]
            with self.assertRaises(preflight.Rejected):
                preflight.validate_config(candidate)

    @unittest.skipUnless(os.getenv("SCM_TEST_COMPOSE"), "standalone Compose not supplied")
    def test_real_compose_2_20_1_with_synthetic_env(self):
        env = copy.deepcopy(config()["services"]["backend"]["environment"])
        for name in ("SCM_DATABASE_SOCKET_DIR",):
            env.pop(name)
        with tempfile.TemporaryDirectory(prefix="scm-compose-test-") as directory:
            path = Path(directory) / ".env"
            path.write_text("\n".join(f"{key}={value}" for key, value in env.items()) + "\n", encoding="utf-8")
            path.chmod(0o600)
            resolved = preflight.compose_config(os.environ["SCM_TEST_COMPOSE"], path)
            preflight.validate_config(resolved)
            self.assertEqual(resolved["services"]["backend"]["volumes"][0]["read_only"], True)
            self.assertEqual(resolved["services"]["db-relay"]["entrypoint"], ["python", "-m", "app.db.relay"])
            self.assertNotIn("asset-postgres", resolved["services"])


if __name__ == "__main__":
    unittest.main()
