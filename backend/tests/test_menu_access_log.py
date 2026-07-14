import unittest

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.menu_access_log import MenuAccessLog
from app.models.user import User
from app.schemas.menu_access_log import MenuAccessLogCreate
from app.services.menu_access_log_service import (
    MENU_ACCESS_TARGETS,
    MenuAccessDeniedError,
    MenuAccessPayloadError,
    get_menu_access_logs,
    record_menu_access_log,
)


def make_request(client_ip="192.168.222.10"):
    return Request({
        "type": "http", "method": "POST", "path": "/access-logs/menu",
        "headers": [(b"user-agent", b"Mozilla/5.0 Windows NT 10.0 Chrome/126.0")],
        "client": (client_ip, 12345), "server": ("testserver", 8010),
        "scheme": "http", "query_string": b"",
    })


def make_user(role="user", permissions=None):
    user = User(id=1, username="tester", name="테스트", password_hash="-", role=role)
    user.menu_permissions = permissions or []
    return user


def payload(key, name, path):
    return MenuAccessLogCreate(menu_key=key, menu_name=name, route_path=path)


class MenuAccessLogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[MenuAccessLog.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_records_server_owned_user_and_request_metadata(self):
        result = record_menu_access_log(
            self.db, make_request(), make_user("admin"),
            payload("hr_list", "인사업무 > 리스트", "/hr/list"),
        )
        log = self.db.query(MenuAccessLog).one()
        self.assertTrue(result.recorded)
        self.assertEqual(log.username, "tester")
        self.assertEqual(log.ip_address, "192.168.222.10")
        self.assertEqual(log.access_type, "internal")
        self.assertEqual(log.browser, "Chrome")

    def test_rejects_unpermitted_or_forged_menu(self):
        with self.assertRaises(MenuAccessDeniedError):
            record_menu_access_log(
                self.db, make_request(), make_user(),
                payload("settings", "설정", "/settings"),
            )
        with self.assertRaises(MenuAccessPayloadError):
            record_menu_access_log(
                self.db, make_request(), make_user(permissions=["hr_list"]),
                payload("hr_list", "다른 메뉴", "/hr/list"),
            )

    def test_deduplicates_consecutive_same_menu_but_allows_return_after_other_menu(self):
        user = make_user("admin")
        hr = payload("hr_list", "인사업무 > 리스트", "/hr/list")
        history = payload("history", "변경 이력", "/history")
        self.assertTrue(record_menu_access_log(self.db, make_request(), user, hr).recorded)
        duplicate = record_menu_access_log(self.db, make_request(), user, hr)
        self.assertTrue(duplicate.deduplicated)
        self.assertTrue(record_menu_access_log(self.db, make_request(), user, history).recorded)
        self.assertTrue(record_menu_access_log(self.db, make_request(), user, hr).recorded)
        self.assertEqual(self.db.query(MenuAccessLog).count(), 3)

    def test_filters_and_paginates_newest_first(self):
        user = make_user("admin")
        record_menu_access_log(self.db, make_request("8.8.8.8"), user, payload("history", "변경 이력", "/history"))
        result = get_menu_access_logs(
            self.db, keyword="8.8", username="test", menu_key="history",
            access_type="external", start_date=None, end_date=None, page=1, page_size=50,
        )
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].menu_key, "history")
        self.assertEqual(result.menu_options, [{"menu_key": "history", "menu_name": "변경 이력"}])

    def test_all_sidebar_menu_targets_are_accepted_for_admin(self):
        sidebar_keys = {
            "dashboard", "drink_orders", "work_manual", "vendor_contacts",
            "expiration_schedules", "assets", "software", "company_cars",
            "fire_insurance", "access_info", "equipment_status", "excel_management", "statistics",
            "history", "install_files", "hr_list", "scm", "user_management", "settings",
        }
        self.assertTrue(sidebar_keys.issubset(set(MENU_ACCESS_TARGETS)))
        user = make_user("admin")
        for key in sorted(sidebar_keys):
            target = MENU_ACCESS_TARGETS[key]
            result = record_menu_access_log(
                self.db, make_request(), user,
                payload(key, target["name"], target["path"]),
            )
            self.assertTrue(result.recorded, key)

    def test_normal_user_can_record_only_permitted_sidebar_menu(self):
        user = make_user(permissions=["dashboard", "assets"])
        dashboard = MENU_ACCESS_TARGETS["dashboard"]
        self.assertTrue(record_menu_access_log(
            self.db, make_request(), user,
            payload("dashboard", dashboard["name"], dashboard["path"]),
        ).recorded)
        software = MENU_ACCESS_TARGETS["software"]
        with self.assertRaises(MenuAccessDeniedError):
            record_menu_access_log(
                self.db, make_request(), user,
                payload("software", software["name"], software["path"]),
            )

    def test_split_network_menus_are_recorded_independently(self):
        user = make_user(permissions=["access_info", "equipment_status"])
        access = MENU_ACCESS_TARGETS["access_info"]
        equipment = MENU_ACCESS_TARGETS["equipment_status"]
        self.assertTrue(record_menu_access_log(
            self.db, make_request(), user,
            payload("access_info", access["name"], access["path"]),
        ).recorded)
        self.assertTrue(record_menu_access_log(
            self.db, make_request(), user,
            payload("equipment_status", equipment["name"], equipment["path"]),
        ).recorded)
        self.assertEqual(
            [row.menu_key for row in self.db.query(MenuAccessLog).order_by(MenuAccessLog.id).all()],
            ["access_info", "equipment_status"],
        )

    def test_excel_import_uses_hr_route_and_requires_admin(self):
        excel = payload("excel_import", "엑셀 일괄등록", "/hr/list")
        with self.assertRaises(MenuAccessDeniedError):
            record_menu_access_log(self.db, make_request(), make_user(permissions=["hr_list"]), excel)
        self.assertTrue(record_menu_access_log(self.db, make_request(), make_user("admin"), excel).recorded)

    def test_logging_database_failure_is_best_effort(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        db = Session(engine)
        try:
            with self.assertLogs("app.services.menu_access_log_service", level="ERROR"):
                result = record_menu_access_log(
                    db, make_request(), make_user("admin"),
                    payload("settings", "설정", "/settings"),
                )
            self.assertFalse(result.recorded)
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
