import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.main import app
from app.services.private_image_path import resolve_private_image_path
from app.api.routers.work_manuals import is_safe_work_manual_image_url


class PrivateUploadAccessTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "assets").mkdir()
        (self.root / "assets" / "image.png").write_bytes(b"private-image")
        (self.root / "beverage-orders").mkdir()
        (self.root / "beverage-orders" / "receipt.png").write_bytes(b"receipt-image")
        (self.root / "work_manuals" / "images").mkdir(parents=True)
        self.manual_name = "a" * 32 + ".png"
        (self.root / "work_manuals" / "images" / self.manual_name).write_bytes(b"manual-image")
        self.settings_patch = patch.object(settings, "upload_dir", str(self.root))
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        app.dependency_overrides[get_db] = lambda: Mock()
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def authorize(self, permissions):
        user = SimpleNamespace(id=7, role="user", menu_permissions=permissions, is_active=True)
        app.dependency_overrides[get_current_user] = lambda: user

    def test_upload_mount_is_gone_and_image_requires_auth(self):
        self.assertEqual(self.client.get("/uploads/assets/image.png").status_code, 404)
        self.assertEqual(self.client.get("/uploads/other.txt").status_code, 404)
        self.assertEqual(self.client.get("/assets/1/spec-image").status_code, 401)
        self.assertEqual(self.client.get("/work-manuals/images/" + self.manual_name).status_code, 401)

    def test_asset_image_requires_menu_permission_and_stays_inside_root(self):
        with patch("app.routers.assets.get_asset", return_value=SimpleNamespace(spec_image_path="assets/image.png")):
            self.authorize([])
            self.assertEqual(self.client.get("/assets/1/spec-image").status_code, 403)
            self.authorize(["assets"])
            response = self.client.get("/assets/1/spec-image")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"private-image")
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["content-disposition"], "inline")

        with patch("app.routers.assets.get_asset", return_value=SimpleNamespace(spec_image_path="../secret.txt")):
            self.assertEqual(self.client.get("/assets/1/spec-image").status_code, 404)

    def test_manual_image_requires_menu_permission_and_safe_filename(self):
        self.authorize([])
        self.assertEqual(self.client.get("/work-manuals/images/" + self.manual_name).status_code, 403)
        self.authorize(["work_manual"])
        response = self.client.get("/work-manuals/images/" + self.manual_name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"manual-image")
        self.assertEqual(self.client.get("/work-manuals/images/not-a-stored-file.png").status_code, 404)

    def test_beverage_image_requires_menu_permission(self):
        record = SimpleNamespace(image_path="beverage-orders/receipt.png")
        with patch("app.api.routers.beverage_orders.get_beverage_order_record", return_value=record):
            self.authorize([])
            self.assertEqual(self.client.get("/beverage-orders/2/image").status_code, 403)
            self.authorize(["drink_orders"])
            response = self.client.get("/beverage-orders/2/image")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"receipt-image")

    def test_path_traversal_and_symlink_escape_are_rejected(self):
        for value in ("../secret.txt", "/etc/passwd", "assets/../../secret.txt"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_private_image_path(value, "assets")
        outside = self.root / "outside.png"
        outside.write_bytes(b"secret")
        link = self.root / "assets" / "link.png"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(ValueError):
            resolve_private_image_path("assets/link.png", "assets")

    def test_legacy_manual_content_remains_accepted_without_public_mount(self):
        self.assertTrue(is_safe_work_manual_image_url("/uploads/work_manuals/images/" + self.manual_name))
        self.assertTrue(is_safe_work_manual_image_url("/work-manuals/images/" + self.manual_name))
        self.assertFalse(is_safe_work_manual_image_url("/work-manuals/images/../secret.png"))


if __name__ == "__main__":
    unittest.main()
