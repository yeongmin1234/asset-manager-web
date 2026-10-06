import asyncio
import hashlib
import io
import os
import socket
import threading
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import jwt
import httpx
import uvicorn
from fastapi.testclient import TestClient
from starlette.responses import FileResponse

from app.main import app
from app.db.database import get_db
from app.models.user import User
from app.models.attachment import AttachmentEntityType
from app.services.download_service import DownloadMiddleware, disposition

SECRET = "test-download-secret-not-for-production-0123456789"


class NativeDownloadsTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.path = self.root / "한글 설치 자료 (1).zip"
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr("설명.txt", "테스트 파일")
        self.user = User(id=91, username="download-test", name="Test", role="admin", is_active=True, password_hash="-")
        self.db = Mock()
        self.db.get.return_value = self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.pop, get_db)
        for module in ["app.core.auth", "app.services.download_service"]:
            self.stack.enter_context(patch(module + "._get_jwt_secret", return_value=SECRET))
        self.item = SimpleNamespace(id=1, original_filename=self.path.name, file_path=str(self.path),
                                    mime_type="application/pdf", entity_type=AttachmentEntityType.WORK_MANUAL)
        for module in ["app.services.install_file_service", "app.api.routers.install_files"]:
            self.stack.enter_context(patch(module + ".get_install_file", return_value=self.item))
            self.stack.enter_context(patch(module + ".resolve_install_file_path", return_value=self.path))
        for module in ["app.services.attachment_service", "app.api.routers.attachments"]:
            self.stack.enter_context(patch(module + ".get_attachment", return_value=self.item))
            self.stack.enter_context(patch(module + ".resolve_attachment_path", return_value=self.path))
        self.count = self.stack.enter_context(patch("app.api.routers.install_files.increment_install_file_download_count", return_value=self.item))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def bearer(self, expired=False):
        exp = datetime.now(timezone.utc) + timedelta(seconds=-10 if expired else 300)
        return {"Authorization": "Bearer " + jwt.encode({"sub": "91", "exp": exp}, SECRET, algorithm="HS256")}

    def prepare(self, path="/install-files/1/download", **kwargs):
        return self.client.get("/downloads/prepare", params={"path": path, **kwargs}, headers=self.bearer())

    def transfer(self, ticket, download_id=None):
        if download_id is None:
            try:
                download_id = jwt.decode(ticket, options={"verify_signature": False})["jti"]
            except (jwt.PyJWTError, KeyError):
                download_id = "0" * 32
        return self.client.post("/downloads/transfer", data={"ticket": ticket, "download_id": download_id})

    def test_native_zip_exact_bytes_unicode_headers_and_single_counter(self):
        response = self.prepare()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertRegex(response.json()["download_id"], r"^[a-f0-9]{32}$")
        self.count.assert_not_called()
        result = self.transfer(response.json()["ticket"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, self.path.read_bytes())
        self.assertEqual(int(result.headers["content-length"]), self.path.stat().st_size)
        self.assertIn("filename*=UTF-8''", result.headers["content-disposition"])
        with zipfile.ZipFile(io.BytesIO(result.content)) as archive:
            self.assertIsNone(archive.testzip())
        self.count.assert_called_once()

    def test_missing_file_and_denied_permission(self):
        self.path.unlink()
        self.assertEqual(self.prepare().status_code, 404)
        self.user.role = "user"
        self.user.menu_permissions = []
        self.assertEqual(self.prepare().status_code, 403)
        self.assertEqual(self.prepare("/attachments/1/download").status_code, 403)

    def test_session_expired_missing_and_invalid_ticket(self):
        self.assertEqual(self.client.get("/downloads/prepare", params={"path": "/install-files/1/download"}).status_code, 401)
        self.assertEqual(self.client.get("/downloads/prepare", params={"path": "/install-files/1/download"}, headers=self.bearer(True)).status_code, 401)
        self.assertEqual(self.transfer("invalid-secret").status_code, 401)
        ticket = self.prepare().json()["ticket"]
        payload = jwt.decode(ticket, SECRET, algorithms=["HS256"], audience="native-download")
        payload["exp"] = 1
        self.assertEqual(self.transfer(jwt.encode(payload, SECRET, algorithm="HS256")).status_code, 401)

    def test_permission_and_file_rechecked_at_transfer(self):
        ticket = self.prepare().json()["ticket"]
        self.user.role = "user"
        self.assertEqual(self.transfer(ticket).status_code, 403)
        self.user.role = "admin"
        self.path.unlink()
        response = self.transfer(ticket)
        self.assertEqual(response.status_code, 404)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("asset-manager-download-error", response.text)
        self.assertNotIn("<h1>", response.text)
        self.assertNotIn("원래 화면", response.text)

    def test_ticket_cannot_authenticate_other_routes_or_be_changed(self):
        ticket = self.prepare().json()["ticket"]
        response = self.client.get("/install-files/1/download", headers={"Authorization": "Bearer " + ticket})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.prepare("/users").status_code, 400)
        self.assertEqual(self.prepare("/install-files/../1/download").status_code, 400)
        self.assertEqual(self.transfer(ticket + "tamper").status_code, 401)

    def test_excel_templates_and_pdf_exe(self):
        for path in ["/assets/import/template", "/hr/accounts/import/template"]:
            response = self.transfer(self.prepare(path).json()["ticket"])
            self.assertEqual(response.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                self.assertIsNone(archive.testzip())
        for name, content in [("설치 파일.exe", b"MZ-test"), ("설명 (한글).pdf", b"%PDF-1.4\n%%EOF")]:
            self.path.write_bytes(content)
            self.item.original_filename = name
            response = self.transfer(self.prepare().json()["ticket"])
            self.assertEqual(response.content, content)
        response = self.transfer(self.prepare("/attachments/1/preview").json()["ticket"])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-disposition"].startswith("inline;"))

    def test_exports_reuse_existing_generators(self):
        with patch("app.routers.assets.get_assets", return_value=[]), patch("app.api.routers.admin.query_audit_logs_for_export", return_value=[]), patch("app.api.routers.admin.record_audit_log"):
            for path in ["/assets/export/excel", "/admin/audit-logs/export"]:
                response = self.transfer(self.prepare(path, query="keyword=test").json()["ticket"])
                self.assertEqual(response.status_code, 200)
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    self.assertIsNone(archive.testzip())

    def test_failure_log_has_context_without_credentials(self):
        with self.assertLogs("app.downloads", level="ERROR") as captured:
            self.path.unlink()
            self.prepare()
        text = " ".join(captured.output)
        for field in ["user_id", "file_id", "request_time", "api", "http_status", "reason"]:
            self.assertIn(field, text)
        self.assertNotIn("filename", text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("Authorization", text)

    def test_disposition_special_characters(self):
        header = disposition('한글 "이름" (1);%.pdf\r\n')
        header.encode("ascii")
        self.assertIn("filename*=UTF-8''", header)
        self.assertNotIn("\r", header)
        self.assertNotIn("\n", header)


class BoundedFileStreamingTest(unittest.IsolatedAsyncioTestCase):
    async def test_128mb_and_optional_1740mb_zip(self):
        sizes = [128 * 1024 * 1024]
        if os.environ.get("DOWNLOAD_LARGE_TESTS") == "1":
            sizes.append(1740 * 1024 * 1024)
        for size in sizes:
            with self.subTest(size=size), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "대용량 파일 (검증).zip"
                chunk = b"x" * (1024 * 1024)
                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                    with archive.open("payload.bin", "w", force_zip64=True) as member:
                        for _ in range(size // len(chunk)):
                            member.write(chunk)
                expected = hashlib.sha256()
                with path.open("rb") as source:
                    while data := source.read(1024 * 1024):
                        expected.update(data)
                received = hashlib.sha256()
                count = 0
                largest = 0

                async def sink(message):
                    nonlocal count, largest
                    if message["type"] == "http.response.body":
                        data = message.get("body", b"")
                        received.update(data)
                        count += len(data)
                        largest = max(largest, len(data))

                async def receive():
                    await asyncio.Event().wait()

                response = FileResponse(path, filename=path.name)
                scope = {"type": "http", "method": "GET", "path": "/install-files/1/download", "headers": [], "asgi": {"spec_version": "2.4"}}
                await DownloadMiddleware(response)(scope, receive, sink)
                self.assertEqual(count, path.stat().st_size)
                self.assertEqual(received.hexdigest(), expected.hexdigest())
                self.assertLessEqual(largest, 1024 * 1024)
                with zipfile.ZipFile(path) as archive:
                    self.assertIsNone(archive.testzip())
                # Real loopback HTTP transfer through the native POST adapter.
                # Isolated app, random ephemeral port, no production lifespan/DB.
                ready = threading.Event()

                class TestServer(uvicorn.Server):
                    async def startup(self, sockets=None):
                        await super().startup(sockets=sockets)
                        ready.set()

                listener = socket.socket()
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
                self.assertNotIn(port, [80, 8080])
                server = TestServer(uvicorn.Config(DownloadMiddleware(response), lifespan="off", access_log=False, log_level="error"))
                worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
                with patch("app.services.download_service._get_jwt_secret", return_value=SECRET):
                    worker.start()
                    try:
                        self.assertTrue(await asyncio.to_thread(ready.wait, 10))
                        download_id = "1" * 32
                        ticket = jwt.encode({"sub": "91", "aud": "native-download", "jti": download_id, "path": scope["path"], "query": "", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(seconds=90)}, SECRET, algorithm="HS256")

                        def receive_http():
                            digest = hashlib.sha256()
                            total = 0
                            with httpx.stream("POST", "http://127.0.0.1:{}/downloads/transfer".format(port), data={"ticket": ticket, "download_id": download_id}, timeout=60, trust_env=False) as result:
                                result.raise_for_status()
                                self.assertEqual(int(result.headers["content-length"]), path.stat().st_size)
                                for block in result.iter_bytes(65536):
                                    digest.update(block)
                                    total += len(block)
                            return total, digest.hexdigest()

                        total, digest = await asyncio.to_thread(receive_http)
                        self.assertEqual(total, path.stat().st_size)
                        self.assertEqual(digest, expected.hexdigest())
                    finally:
                        server.should_exit = True
                        await asyncio.to_thread(worker.join, 10)
                        listener.close()
                        self.assertFalse(worker.is_alive())

    async def test_midstream_failure_is_logged_and_propagated(self):
        async def broken(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"partial", "more_body": True})
            raise OSError("read failed")

        async def noop(*args):
            pass

        with self.assertLogs("app.downloads", level="ERROR") as captured:
            with self.assertRaises(OSError):
                await DownloadMiddleware(broken)({"type": "http", "method": "GET", "path": "/install-files/1/download", "headers": []}, noop, noop)
        self.assertIn("OSError", " ".join(captured.output))
