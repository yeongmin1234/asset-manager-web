import builtins
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo as StandardZoneInfo, ZoneInfoNotFoundError

# Load third-party dependencies before the import hook is installed. The hook
# must emulate only the target modules running on Python 3.8, not Pydantic or
# SQLAlchemy importing their own standard-library dependencies.
import app.schemas.inventory_snapshot  # noqa: F401,E402
import app.services.inventory_change_analysis_service  # noqa: F401,E402
import app.services.inventory_snapshot_query_service  # noqa: F401,E402


BACKEND_DIR = Path(__file__).resolve().parents[1]
MODULE_PATHS = (
    "app/schemas/inventory_snapshot.py",
    "app/services/inventory_change_analysis_service.py",
    "app/services/inventory_snapshot_query_service.py",
)


class ZoneInfoCompatibilityTest(unittest.TestCase):
    def test_modules_fall_back_to_backports_zoneinfo(self):
        real_import = builtins.__import__
        fake_backport = SimpleNamespace(
            ZoneInfo=StandardZoneInfo,
            ZoneInfoNotFoundError=ZoneInfoNotFoundError,
        )

        def compatible_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "zoneinfo":
                raise ImportError("simulated Python 3.8")
            if name == "backports.zoneinfo":
                return fake_backport
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=compatible_import):
            for index, relative_path in enumerate(MODULE_PATHS):
                with self.subTest(path=relative_path):
                    spec = importlib.util.spec_from_file_location(
                        "zoneinfo_compat_{}".format(index), BACKEND_DIR / relative_path,
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.assertIs(module.ZoneInfo, StandardZoneInfo)


if __name__ == "__main__":
    unittest.main()
