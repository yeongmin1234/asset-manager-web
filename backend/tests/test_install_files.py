import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.main import app
from app.models.user import User
from app.services.install_file_service import (
    InstallFileValidationError,
    cleanup_install_upload,
    save_install_upload,
    validate_original_filename,
)


def admin_user():
    return User(id=1, username="admin", name="관리자", password_hash="-", role="admin")


class InstallFileServiceTest(unittest.IsolatedAsyncioTestCase):
    def test_allowed_extensions_are_case_insensitive(self):
        for extension in ("EXE", "msi", "ZIP", "7z", "PDF", "txt", "BAT", "ps1"):
            self.assertEqual(validate_original_filename(f"설치 파일.{extension}"), f"설치 파일.{extension}")

    def test_disallowed_extension_is_rejected(self):
        with self.assertRaisesRegex(InstallFileValidationError, "허용되지 않는 파일 형식"):
            validate_original_filename("malware.com")

    async def test_korean_space_filename_upload_and_duplicate_names_are_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.install_file_service.get_install_file_upload_dir",
            return_value=Path(temp_dir),
        ):
            first = await save_install_upload(UploadFile(io.BytesIO(b"exe-one"), filename="한글 설치 파일.EXE"))
            second = await save_install_upload(UploadFile(io.BytesIO(b"exe-two"), filename="한글 설치 파일.EXE"))
            self.assertNotEqual(first["stored_filename"], second["stored_filename"])
            self.assertEqual(first["file_extension"], ".exe")
            self.assertTrue(Path(first["file_path"]).is_file())
            self.assertTrue(Path(second["file_path"]).is_file())

    async def test_exe_msi_and_zip_files_are_written(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.install_file_service.get_install_file_upload_dir",
            return_value=Path(temp_dir),
        ):
            for filename in ("installer.exe", "installer.msi", "archive.zip"):
                result = await save_install_upload(UploadFile(io.BytesIO(b"content"), filename=filename))
                self.assertTrue(Path(result["file_path"]).is_file())

    async def test_size_limit_removes_temporary_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.install_file_service.get_install_file_upload_dir", return_value=Path(temp_dir),
        ), patch("app.services.install_file_service.get_max_install_file_size", return_value=3):
            with self.assertRaisesRegex(InstallFileValidationError, "파일 크기"):
                await save_install_upload(UploadFile(io.BytesIO(b"1234"), filename="large.zip"))
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_cleanup_removes_only_new_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.install_file_service.get_install_file_upload_dir", return_value=Path(temp_dir),
        ):
            target = Path(temp_dir) / "new-file.exe"
            target.write_bytes(b"new")
            cleanup_install_upload({"file_path": str(target)})
            self.assertFalse(target.exists())


class InstallFileRouteTest(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_multipart_create_returns_201_and_matching_fields(self):
        db = Mock()
        user = admin_user()
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[require_admin] = lambda: user
        app.dependency_overrides[get_db] = lambda: db
        now = datetime.now(timezone.utc)
        result = SimpleNamespace(
            id=1, title="LG Update", category="드라이버", os_type="Windows", version="1.0",
            description="설명", install_guide="설치", caution_note="주의",
            original_filename="LG Update Installer.exe", file_size=1284656, file_extension=".exe",
            is_required=False, install_order=0, download_count=0, created_at=now, updated_at=now,
        )
        upload_data = {
            "original_filename": result.original_filename, "stored_filename": "safe.exe",
            "file_path": "/safe/safe.exe", "file_size": result.file_size, "file_extension": ".exe",
        }
        with patch("app.api.routers.install_files.verify_admin_guard"), patch(
            "app.api.routers.install_files.save_install_upload", return_value=upload_data,
        ), patch("app.api.routers.install_files.create_install_file", return_value=result) as create, patch(
            "app.api.routers.install_files.record_audit_log", return_value=True,
        ):
            response = TestClient(app, raise_server_exceptions=False).post(
                "/install-files",
                data={
                    "title": "LG Update", "category": "드라이버", "os_type": "Windows",
                    "version": "1.0", "description": "설명", "install_guide": "설치",
                    "caution_note": "주의", "is_required": "false", "install_order": "0",
                    "admin_password": "password",
                },
                files={"file": ("LG Update Installer.exe", b"MZ", "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 201, response.text)
        create.assert_called_once()
        self.assertEqual(create.call_args.args[0], db)
        self.assertEqual(create.call_args.args[1]["install_guide"], "설치")
        self.assertEqual(create.call_args.args[2], upload_data)

    def test_missing_file_is_422(self):
        user = admin_user()
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[require_admin] = lambda: user
        app.dependency_overrides[get_db] = lambda: Mock()
        response = TestClient(app, raise_server_exceptions=False).post(
            "/install-files", data={"title": "자료", "admin_password": "password"},
        )
        self.assertEqual(response.status_code, 422)

    def test_non_admin_is_403(self):
        user = User(id=2, username="user", name="사용자", password_hash="-", role="user")
        app.dependency_overrides[get_current_user] = lambda: user
        response = TestClient(app, raise_server_exceptions=False).post(
            "/install-files",
            data={"title": "자료", "admin_password": "password"},
            files={"file": ("file.zip", b"zip", "application/zip")},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
