import json
import logging
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.config import Settings
from app.main import app
from app.models.user import User
from app.services.ecount_api_service import (
    EcountApiError,
    EcountApiService,
    EcountAuthResult,
    EcountConfigurationError,
    EcountTimeoutError,
    clear_ecount_session_cache,
)


API_KEY = "secret-api-cert-key-for-test"
SESSION_ID = "secret-session-id-for-test"


def make_settings(**overrides):
    values = {
        "ecount_enabled": True,
        "ecount_company_code": "123456",
        "ecount_user_id": "api-user",
        "ecount_api_cert_key": API_KEY,
        "ecount_api_mode": "test",
        "ecount_request_timeout": 15,
        "ecount_trust_ssl": True,
    }
    values.update(overrides)
    return Settings(**values)


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


class EcountApiServiceTest(unittest.TestCase):
    def setUp(self):
        clear_ecount_session_cache()

    def tearDown(self):
        clear_ecount_session_cache()

    def test_missing_required_settings_are_distinguished(self):
        cases = (
            ("ecount_company_code", "회사코드"),
            ("ecount_user_id", "사용자 ID"),
            ("ecount_api_cert_key", "인증키"),
        )
        for field, expected in cases:
            with self.subTest(field=field):
                service = EcountApiService(make_settings(**{field: ""}))
                with self.assertRaises(EcountConfigurationError) as context:
                    service.validate_settings()
                self.assertIn(expected, context.exception.message)
                self.assertNotIn(API_KEY, context.exception.message)

    def test_zone_lookup_success(self):
        def handler(request):
            self.assertEqual(json.loads(request.content)["COM_CODE"], "123456")
            return httpx.Response(200, json={"Status": "200", "Data": {"ZONE": "AA"}})

        with make_client(handler) as client:
            self.assertEqual(EcountApiService(make_settings(), client).get_zone(), "AA")

    def test_zone_lookup_failure(self):
        with make_client(lambda request: httpx.Response(200, json={"Status": "500", "Error": {"Code": "Z001"}})) as client:
            with self.assertRaises(EcountApiError) as context:
                EcountApiService(make_settings(), client).get_zone()
        self.assertEqual(context.exception.kind, "zone_failed")

    def test_login_success_only_returns_boolean(self):
        def handler(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["API_CERT_KEY"], API_KEY)
            self.assertEqual(payload["ZONE"], "AA")
            return httpx.Response(200, json={"Status": 200, "Data": {"Datas": {"SESSION_ID": SESSION_ID}}})

        with make_client(handler) as client:
            result = EcountApiService(make_settings(), client).authenticate("AA")
        self.assertIs(result, True)
        self.assertNotIn(SESSION_ID, repr(result))

    def test_login_failure(self):
        with make_client(lambda request: httpx.Response(200, json={"Status": "401", "Error": {"Code": "AUTH"}})) as client:
            with self.assertRaises(EcountApiError) as context:
                EcountApiService(make_settings(), client).authenticate("AA")
        self.assertEqual(context.exception.kind, "authentication_failed")

    def test_missing_session_id_is_rejected(self):
        with make_client(lambda request: httpx.Response(200, json={"Status": "200", "Data": {}})) as client:
            with self.assertRaises(EcountApiError) as context:
                EcountApiService(make_settings(), client).authenticate("AA")
        self.assertEqual(context.exception.kind, "session_not_issued")

    def test_timeout_is_distinguished(self):
        def handler(request):
            raise httpx.ReadTimeout("slow", request=request)

        with make_client(handler) as client:
            with self.assertRaises(EcountTimeoutError):
                EcountApiService(make_settings(), client).get_zone()

    def test_secrets_are_not_logged_on_failure(self):
        with make_client(lambda request: httpx.Response(200, json={"Status": "500", "Error": {"Code": "SAFE_CODE"}})) as client:
            with self.assertLogs("app.services.ecount_api_service", logging.WARNING) as captured:
                with self.assertRaises(EcountApiError):
                    EcountApiService(make_settings(), client).authenticate("AA")
        output = " ".join(captured.output)
        self.assertIn("SAFE_CODE", output)
        self.assertNotIn(API_KEY, output)
        self.assertNotIn(SESSION_ID, output)

    def test_test_connection_discards_session_id(self):
        responses = iter((
            httpx.Response(200, json={"Status": "200", "Data": {"ZONE": "AA"}}),
            httpx.Response(200, json={"Status": "200", "Data": {"SESSION_ID": SESSION_ID}}),
        ))
        with make_client(lambda request: next(responses)) as client:
            result = EcountApiService(make_settings(), client).test_connection().as_dict()
        self.assertTrue(result["authenticated"])
        self.assertNotIn(SESSION_ID, repr(result))
        self.assertNotIn("session", " ".join(result.keys()).lower())

    def test_authenticated_session_is_reused_from_memory(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            if request.url.path.endswith("/Zone"):
                return httpx.Response(200, json={"Status": "200", "Data": {"ZONE": "AA"}})
            return httpx.Response(200, json={"Status": "200", "Data": {"SESSION_ID": SESSION_ID}})

        config = make_settings(ecount_api_mode="production")
        with make_client(handler) as client:
            service = EcountApiService(config, client)
            first = service.get_authenticated_session()
            second = service.get_authenticated_session()
        self.assertIs(first, second)
        self.assertEqual(len(calls), 2)


class EcountAdminRouteTest(unittest.TestCase):
    def test_admin_route_returns_safe_success_response(self):
        safe_result = EcountAuthResult(True, True, "test", "AA", True, "이카운트 API 인증에 성공했습니다.", 12)
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, username="admin", name="관리자", password_hash="-", role="admin",
        )
        try:
            with patch("app.api.routers.ecount_integration.EcountApiService") as service_class:
                service_class.return_value.test_connection.return_value = safe_result
                api_response = TestClient(app).post("/admin/integrations/ecount/test-auth")
            self.assertEqual(api_response.status_code, 200)
            response = api_response.json()
        finally:
            app.dependency_overrides.clear()
        self.assertTrue(response["authenticated"])
        self.assertNotIn("SESSION_ID", response)
        self.assertNotIn("API_CERT_KEY", response)

    def test_normal_user_is_rejected(self):
        user = User(id=2, username="user", name="일반", password_hash="-", role="user")
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = TestClient(app).post("/admin/integrations/ecount/test-auth")
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 403)

    def test_openapi_contains_admin_test_auth_path(self):
        schema = app.openapi()
        path = schema["paths"]["/admin/integrations/ecount/test-auth"]
        self.assertIn("post", path)


if __name__ == "__main__":
    unittest.main()
