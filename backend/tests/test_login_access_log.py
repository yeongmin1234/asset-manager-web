import unittest

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models.login_access_log import LoginAccessLog
from app.services.login_access_log_service import (
    classify_access_type,
    get_access_logs,
    get_client_ip,
    parse_user_agent,
    record_access_log,
)


def make_request(client_ip, user_agent="", forwarded_for=""):
    headers = []
    if user_agent:
        headers.append((b"user-agent", user_agent.encode("latin-1")))
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": headers,
        "client": (client_ip, 12345),
        "server": ("testserver", 8010),
        "scheme": "http",
        "query_string": b"",
    })


class LoginAccessLogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[LoginAccessLog.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_records_login_metadata_and_classifies_network(self):
        request = make_request(
            "192.168.222.237",
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        )
        record_access_log(
            self.db,
            request,
            user_id=1,
            username="admin",
            user_name="관리자",
            event_type="login",
            login_result="success",
        )

        log = self.db.query(LoginAccessLog).one()
        self.assertEqual(log.ip_address, "192.168.222.237")
        self.assertEqual(log.access_type, "internal")
        self.assertEqual(log.browser, "Chrome")
        self.assertEqual(log.operating_system, "Windows")

    def test_failed_login_reason_and_filters(self):
        record_access_log(
            self.db,
            make_request("8.8.8.8", "Mozilla/5.0 Edg/126.0 Windows NT 10.0"),
            username="missing-user",
            event_type="login",
            login_result="failure",
            failure_reason="존재하지 않는 사용자",
        )
        occurred_date = self.db.query(LoginAccessLog).one().occurred_at.date()

        result = get_access_logs(
            self.db,
            keyword="missing",
            username=None,
            event_type="login",
            login_result="failure",
            access_type="external",
            start_date=occurred_date,
            end_date=occurred_date,
            page=1,
            page_size=50,
        )
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].failure_reason, "존재하지 않는 사용자")
        self.assertEqual(result.items[0].browser, "Edge")

    def test_forwarded_ip_is_only_used_for_configured_proxy(self):
        original = settings.trusted_proxy_ips
        try:
            settings.trusted_proxy_ips = "127.0.0.1"
            self.assertEqual(get_client_ip(make_request("127.0.0.1", forwarded_for="203.0.113.10")), "203.0.113.10")
            self.assertEqual(get_client_ip(make_request("192.168.0.2", forwarded_for="203.0.113.11")), "192.168.0.2")
        finally:
            settings.trusted_proxy_ips = original

    def test_ip_and_user_agent_helpers(self):
        self.assertEqual(classify_access_type("127.0.0.1"), "internal")
        self.assertEqual(classify_access_type("::1"), "internal")
        self.assertEqual(classify_access_type("8.8.8.8"), "external")
        self.assertEqual(parse_user_agent("Mozilla/5.0 (iPhone) Safari/605.1"), ("Safari", "iOS"))

    def test_logging_failure_does_not_escape_authentication_flow(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        db = Session(engine)
        try:
            with self.assertLogs("app.services.login_access_log_service", level="ERROR"):
                record_access_log(
                    db,
                    make_request("127.0.0.1"),
                    username="admin",
                    event_type="login",
                    login_result="success",
                )
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
