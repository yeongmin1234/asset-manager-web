import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import UploadFile

from app.models.attachment import AttachmentEntityType
from app.models.user import User
from app.services.attachment_service import (
    AttachmentSizeError,
    AttachmentValidationError,
    create_attachment,
    validate_mime_type,
    validate_original_filename,
)


def admin_user():
    return User(id=1, username="admin", name="관리자", password_hash="-", role="admin")


class AttachmentValidationTest(unittest.TestCase):
    def test_all_documented_extensions_and_uppercase_are_allowed(self):
        extensions = (
            "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp",
            "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "zip",
        )
        for extension in extensions:
            original, normalized = validate_original_filename("한글 업무 설명.{}".format(extension.upper()))
            self.assertEqual(original, "한글 업무 설명.{}".format(extension.upper()))
            self.assertEqual(normalized, ".{}".format(extension))

    def test_unsupported_and_executable_double_extensions_are_rejected(self):
        for filename in ("data.csv", "document.pdf.exe", "document.exe.pdf", "script.JS.txt"):
            with self.subTest(filename=filename), self.assertRaisesRegex(
                AttachmentValidationError, "지원하지 않는 파일 형식"
            ):
                validate_original_filename(filename)

    def test_path_manipulation_is_rejected(self):
        for filename in ("../manual.pdf", "folder/manual.pdf", "folder\\manual.pdf"):
            with self.subTest(filename=filename), self.assertRaises(AttachmentValidationError):
                validate_original_filename(filename)

    def test_mime_is_auxiliary_and_octet_stream_does_not_block_valid_files(self):
        for extension in (".pdf", ".jpg", ".png", ".gif", ".webp", ".bmp", ".docx", ".xlsx", ".pptx", ".txt", ".zip"):
            validate_mime_type(extension, "application/octet-stream")
        with self.assertRaises(AttachmentValidationError):
            validate_mime_type(".pdf", "application/x-msdownload")


class AttachmentStorageTest(unittest.IsolatedAsyncioTestCase):
    async def _create(self, root, filename="한글 업무 설명.PDF", content=b"pdf", content_type="application/pdf", db=None):
        database = db or Mock()
        database.get.return_value = object()
        target = Path(root) / "attachments" / "work_manuals" / "stored.pdf"
        with patch(
            "app.services.attachment_service.resolve_upload_relative_path", return_value=target
        ), patch("app.services.attachment_service.record_attachment_activity"):
            result = await create_attachment(
                database,
                entity_type=AttachmentEntityType.WORK_MANUAL,
                entity_id=1,
                upload_file=UploadFile(io.BytesIO(content), filename=filename, headers={"content-type": content_type}),
                description="",
                current_user=admin_user(),
            )
        return result, target, database

    async def test_pdf_korean_space_name_is_saved_with_uuid_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result, target, database = await self._create(temp_dir)
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), b"pdf")
            self.assertEqual(result.original_filename, "한글 업무 설명.PDF")
            self.assertNotEqual(result.stored_filename, result.original_filename)
            database.commit.assert_called_once()

    async def test_duplicate_original_names_get_different_stored_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first, _, _ = await self._create(temp_dir)
            second, _, _ = await self._create(temp_dir)
            self.assertNotEqual(first.stored_filename, second.stored_filename)

    async def test_size_limit_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.attachment_service.get_max_attachment_size", return_value=3
        ):
            with self.assertRaises(AttachmentSizeError):
                await self._create(temp_dir, content=b"1234")
            self.assertEqual(list(Path(temp_dir).rglob("*.uploading")), [])
            self.assertEqual(list(Path(temp_dir).rglob("*.pdf")), [])

    async def test_db_failure_removes_saved_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Mock()
            database.get.return_value = object()
            database.flush.side_effect = SQLAlchemyError("db failed")
            with self.assertRaises(SQLAlchemyError):
                await self._create(temp_dir, db=database)
            self.assertEqual(list(Path(temp_dir).rglob("*.pdf")), [])


if __name__ == "__main__":
    unittest.main()
