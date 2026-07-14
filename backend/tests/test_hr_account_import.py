import unittest
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.hr_account import HrAccount
from app.services.hr_account_service import (
    HrAccountImportValidationError,
    import_hr_accounts,
    preview_hr_accounts_import,
)


def make_workbook(headers, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class HrAccountImportTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[HrAccount.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_preview_matches_aliases_and_detects_row_states(self):
        self.db.add(HrAccount(department="총무팀", name="기존직원"))
        self.db.commit()
        content = make_workbook(
            ["성명", "소속부서", "ERP ID", "다우 계정", "SCMID", "NAS계정"],
            [
                ["신규직원", "개발팀", 1001, "new", "scm-new", "nas-new"],
                ["기존직원", "총무팀", "old", None, None, None],
                [None, "영업팀", None, None, None, None],
                ["신규직원", "개발팀", None, None, None, None],
                [None, None, None, None, None, None],
            ],
        )

        preview = preview_hr_accounts_import(self.db, content)

        self.assertEqual(preview.total_count, 4)
        self.assertEqual(preview.valid_count, 1)
        self.assertEqual(preview.duplicate_count, 2)
        self.assertEqual(preview.error_count, 1)
        self.assertEqual(preview.rows[0].data.erp, "1001")
        self.assertEqual(preview.matched_columns["department"], "소속부서")

    def test_preview_rejects_missing_required_header(self):
        content = make_workbook(["부서", "ERP"], [["총무팀", "erp-id"]])
        with self.assertRaisesRegex(HrAccountImportValidationError, "이름"):
            preview_hr_accounts_import(self.db, content)

    def test_preview_rejects_empty_invalid_and_ambiguous_workbooks(self):
        with self.assertRaisesRegex(HrAccountImportValidationError, "올바른"):
            preview_hr_accounts_import(self.db, b"not-an-excel-file")
        with self.assertRaisesRegex(HrAccountImportValidationError, "등록할 데이터"):
            preview_hr_accounts_import(self.db, make_workbook(["부서", "이름"], []))
        with self.assertRaisesRegex(HrAccountImportValidationError, "부서 컬럼"):
            preview_hr_accounts_import(
                self.db,
                make_workbook(["부서", "소속부서", "이름"], [["총무팀", "총무팀", "홍길동"]]),
            )

    def test_import_skips_or_updates_existing_account(self):
        account = HrAccount(department="총무팀", name="홍길동", erp="before")
        self.db.add(account)
        self.db.commit()
        preview = preview_hr_accounts_import(
            self.db,
            make_workbook(["부서", "이름", "ERP"], [["총무팀", "홍길동", "after"]]),
        )

        skipped = import_hr_accounts(self.db, preview.rows, "skip")
        self.assertEqual(skipped.skipped_count, 1)
        self.assertEqual(self.db.get(HrAccount, account.id).erp, "before")

        updated = import_hr_accounts(self.db, preview.rows, "update")
        self.assertEqual(updated.updated_count, 1)
        self.db.refresh(account)
        self.assertEqual(account.erp, "after")

    def test_import_creates_valid_rows_and_excludes_errors(self):
        preview = preview_hr_accounts_import(
            self.db,
            make_workbook(
                ["부서", "이름", "NAS"],
                [["개발팀", "신규직원", "new-nas"], ["개발팀", None, "invalid"]],
            ),
        )

        result = import_hr_accounts(self.db, preview.rows, "skip")

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.failed_count, 1)
        account = self.db.scalar(select(HrAccount).where(HrAccount.name == "신규직원"))
        self.assertIsNotNone(account)
        self.assertEqual(account.nas, "new-nas")


if __name__ == "__main__":
    unittest.main()
