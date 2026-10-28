"""Post-build offline smoke check against an explicitly supplied local image ID."""
import os
import re
import subprocess
import unittest
from uuid import uuid4


@unittest.skipUnless(os.getenv("SCM_TEST_PREFLIGHT_IMAGE"), "built verifier image not supplied")
class PreflightImageTests(unittest.TestCase):
    def test_built_image_reads_imports_and_executes_verifier_as_nonroot(self):
        image = os.environ["SCM_TEST_PREFLIGHT_IMAGE"]
        self.assertTrue(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", image)), "local_image_id_required")
        cli = ["docker", "--host=unix:///var/run/docker.sock"]
        environment = {key: value for key, value in os.environ.items() if not key.startswith("DOCKER_")}
        name = "scm-preflight-smoke-" + uuid4().hex
        run_requested, result = False, None
        try:
            configured = subprocess.run(cli + ["image", "inspect", "--format", "{{.Config.User}}", image],
                                        env=environment, capture_output=True, timeout=15)
            self.assertTrue(configured.returncode == 0 and configured.stdout.strip() == b"10001:10001",
                            "image_nonroot_user_invalid_output_suppressed")
            run_requested = True
            result = subprocess.run(cli + ["run", "--rm", "--name=" + name, "--pull=never", "--network=none", "--read-only",
                                          "--user=10001:10001", "--cap-drop=ALL",
                                          "--security-opt=no-new-privileges:true", "--memory=256m",
                                          "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--log-driver=none",
                                          "--entrypoint=python", image, "-I", "-B",
                                          "/srv/new-scm/deploy/check_preflight_image.py"],
                                    env=environment, capture_output=True, timeout=45)
        except (OSError, subprocess.TimeoutExpired):
            self.fail("image_smoke_command_unavailable_output_suppressed")
        finally:
            if run_requested and (result is None or not 0 <= result.returncode < 125):
                try:
                    cleanup = subprocess.run(cli + ["rm", "--force", name], env=environment,
                                             capture_output=True, timeout=10)
                    self.assertTrue(cleanup.returncode == 0, "image_smoke_cleanup_failed_output_suppressed")
                except (OSError, subprocess.TimeoutExpired):
                    self.fail("image_smoke_cleanup_failed_output_suppressed")
        self.assertTrue(result.returncode == 0 and result.stdout.strip() == b"PASS verifier_image_nonroot_smoke",
                        "image_smoke_failed_output_suppressed")


if __name__ == "__main__":
    unittest.main()
