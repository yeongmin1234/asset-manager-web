from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
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
from app.services.ecount_api_service import EcountSession
from app.services.inventory_service import (
    clear_inventory_query_cache,
    InventoryError,
    InventoryRateLimitError,
    InventoryResponseError,
    InventoryService,
    InventoryTimeoutError,
)


SESSION_ONE = "private-session-one"
SESSION_TWO = "private-session-two"


def make_settings(**overrides):
    values = {
        "ecount_enabled": True,
        "ecount_company_code": "123456",
        "ecount_user_id": "api-user",
        "ecount_api_cert_key": "private-cert-key",
        "ecount_api_mode": "production",
        "ecount_request_timeout": 15,
        "ecount_trust_ssl": True,
    }
    values.update(overrides)
    return Settings(**values)


def success_response(code="ABC-123", quantity="23.0000000000"):
    return httpx.Response(200, json={
        "Data": {
            "IsSuccess": True,
            "EXPIRE_DATE": "",
            "QUANTITY_INFO": "",
            "TRACE_ID": "trace",
            "TotalCnt": 1,
            "Result": [{"PROD_CD": code, "BAL_QTY": quantity}],
        },
        "Status": "200",
        "Error": None,
    })


def product_response(result, as_json_string=False):
    return httpx.Response(200, json={
        "Data": {
            "IsSuccess": True,
            "Result": json.dumps(result) if as_json_string else result,
        },
        "Status": "200",
        "Error": None,
    })


def location_response(result):
    return httpx.Response(200, json={
        "Data": {"IsSuccess": True, "Result": result},
        "Status": "200",
        "Error": None,
    })


class FakeAuthService:
    def __init__(self):
        self.calls = []

    def get_authenticated_session(self, force_refresh=False):
        self.calls.append(force_refresh)
        return EcountSession(
            session_id=SESSION_TWO if force_refresh else SESSION_ONE,
            zone="AA",
            issued_at=0,
        )


class InventoryServiceTest(unittest.TestCase):
    def setUp(self):
        clear_inventory_query_cache()

    def tearDown(self):
        clear_inventory_query_cache()

    def test_inventory_api_success_and_official_request_shape(self):
        auth = FakeAuthService()

        def handler(request):
            self.assertEqual(request.method, "POST")
            self.assertIn("ViewInventoryBalanceStatus", request.url.path)
            self.assertEqual(request.url.params["SESSION_ID"], SESSION_ONE)
            payload = __import__("json").loads(request.content)
            self.assertEqual(payload["PROD_CD"], "ABC-123")
            self.assertEqual(len(payload["BASE_DATE"]), 8)
            return success_response()

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, auth).search_inventory(item_code="abc-123")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["item_code"], "ABC-123")
        self.assertEqual(result["items"][0]["quantity"], Decimal("23.0000000000"))
        self.assertNotIn("SESSION_ID", repr(result))

    def test_session_expiration_reauthenticates_once(self):
        auth = FakeAuthService()
        calls = []

        def handler(request):
            calls.append(request.url.params["SESSION_ID"])
            if len(calls) == 1:
                return httpx.Response(401, json={
                    "Data": None, "Status": "401", "Error": {"Code": 401, "Message": "Session expired"},
                })
            return success_response()

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, auth).search_inventory(item_code="ABC-123")
        self.assertEqual(result["total"], 1)
        self.assertEqual(auth.calls, [False, True])
        self.assertEqual(calls, [SESSION_ONE, SESSION_TWO])

    def test_authentication_failure_after_retry_is_safe(self):
        auth = FakeAuthService()
        response = httpx.Response(403, json={
            "Data": None, "Status": "403", "Error": {"Code": 403, "Message": "Authentication failed"},
        })
        with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
            with self.assertRaises(InventoryError) as context:
                InventoryService(make_settings(), client, auth).search_inventory(item_code="ABC-123")
        self.assertEqual(auth.calls, [False, True])
        self.assertEqual(context.exception.kind, "authentication_failed")

    def test_korean_authentication_message_reauthenticates_once(self):
        auth = FakeAuthService()
        response = httpx.Response(200, json={
            "Data": None, "Status": "500", "Error": {"Code": 0, "Message": "인증되지 않은 API입니다."},
        })
        with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
            with self.assertRaises(InventoryError) as context:
                InventoryService(make_settings(), client, auth).search_inventory(item_code="ABC")
        self.assertEqual(context.exception.kind, "authentication_failed")
        self.assertEqual(auth.calls, [False, True])

    def test_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("slow", request=request)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(InventoryTimeoutError):
                InventoryService(make_settings(), client, FakeAuthService()).search_inventory(item_code="ABC")

    def test_http_412_is_rate_limit_and_never_reauthenticates(self):
        auth = FakeAuthService()
        limited = httpx.Response(412, json={
            "Data": None, "Status": "412", "Error": {"Code": "RATE", "Message": "private external detail"},
        })
        with httpx.Client(transport=httpx.MockTransport(lambda request: limited)) as client:
            with self.assertRaises(InventoryRateLimitError) as context:
                InventoryService(make_settings(), client, auth).search_inventory(item_code="ABC")
        self.assertEqual(context.exception.kind, "rate_limited")
        self.assertEqual(context.exception.http_status, 412)
        self.assertEqual(auth.calls, [False])
        self.assertNotIn("private external detail", context.exception.message)

    def test_identical_query_uses_60_second_cache(self):
        calls = []

        def handler(request):
            calls.append(request)
            return product_response([{"PROD_CD": "A", "PROD_DES": "토스터블랙"}])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            service = InventoryService(make_settings(), client, FakeAuthService())
            first = service.search_products(keyword="토스터블랙")
            second = service.search_products(keyword="토스터블랙")
        self.assertEqual(len(calls), 1)
        self.assertEqual(first, second)

    def test_concurrent_identical_queries_use_single_external_call(self):
        calls = []

        def handler(request):
            calls.append(request)
            return product_response([{"PROD_CD": "A", "PROD_DES": "토스터블랙"}])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            service = InventoryService(make_settings(), client, FakeAuthService())
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(
                    lambda _: service.search_products(keyword="토스터블랙"),
                    range(2),
                ))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results[0], results[1])

    def test_recommendations_are_sorted_limited_and_product_only(self):
        rows = [
            {"PROD_CD": "4", "PROD_DES": "뉴토스터블랙", "UNIT": "EA"},
            {"PROD_CD": "3", "PROD_DES": "미니토스터", "UNIT": "EA"},
            {"PROD_CD": "2", "PROD_DES": "토스터화이트", "UNIT": "EA"},
            {"PROD_CD": "1", "PROD_DES": "토스터", "UNIT": "EA"},
        ] + [
            {"PROD_CD": str(index), "PROD_DES": "추천토스터{:02d}".format(index), "UNIT": "EA"}
            for index in range(5, 12)
        ]
        paths = []

        def handler(request):
            paths.append(request.url.path)
            return product_response(rows)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).recommend_products("토스터")
        self.assertEqual(result["total"], 11)
        self.assertEqual(len(result["items"]), 8)
        self.assertTrue(result["has_more"])
        self.assertEqual(result["items"][0]["item_name"], "토스터")
        self.assertEqual(result["items"][1]["item_name"], "토스터화이트")
        self.assertEqual(result["items"][-1].keys(), {"item_code", "item_name", "unit"})
        self.assertEqual(len(paths), 1)
        self.assertIn("GetBasicProductsList", paths[0])
        self.assertFalse(any("InventoryBalance" in path for path in paths))

    def test_recommendation_product_code_exact_match(self):
        rows = [
            {"PROD_CD": "101006", "PROD_DES": "토스터블랙", "UNIT": "EA"},
            {"PROD_CD": "X101006", "PROD_DES": "다른 품목", "UNIT": "EA"},
        ]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).recommend_products("101006")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["item_code"], "101006")

    def test_product_name_search_allows_whitespace_difference(self):
        rows = [
            {"PROD_CD": "930101", "PROD_DES": "그린팬 런치박스", "UNIT": "EA"},
            {"PROD_CD": "930102", "PROD_DES": "다른 품목", "UNIT": "EA"},
        ]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).search_products(
                keyword="그린팬런치박스",
            )
        self.assertEqual([item["item_code"] for item in result], ["930101"])

    def test_rate_limit_blocks_followup_external_calls_globally(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(412, text="limited")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            service = InventoryService(make_settings(), client, FakeAuthService())
            with self.assertRaises(InventoryRateLimitError) as first:
                service.search_inventory(item_code="ABC")
            with self.assertRaises(InventoryRateLimitError) as second:
                service.search_inventory(item_code="XYZ")
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(first.exception.retry_after_seconds, 1)
        self.assertGreaterEqual(second.exception.retry_after_seconds, 1)

    def test_cached_product_candidates_remain_available_during_inventory_cooldown(self):
        paths = []
        products = [
            {"PROD_CD": "A1", "PROD_DES": "악세사리 케이스", "UNIT": "EA"},
            {"PROD_CD": "A2", "PROD_DES": "악세사리 거치대", "UNIT": "EA"},
            {"PROD_CD": "R1", "PROD_DES": "레인지 블랙", "UNIT": "EA"},
            {"PROD_CD": "R2", "PROD_DES": "레인지 화이트", "UNIT": "EA"},
        ]

        def handler(request):
            paths.append(request.url.path)
            if "GetBasicProductsList" in request.url.path:
                return product_response(products)
            return httpx.Response(412, text="limited")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            service = InventoryService(make_settings(), client, FakeAuthService())
            first_candidates = service.recommend_products("악세")
            with self.assertRaises(InventoryRateLimitError):
                service.search_inventory(item_code="A1")
            second_candidates = service.recommend_products("레인지")

        self.assertEqual(first_candidates["total"], 2)
        self.assertEqual(second_candidates["total"], 2)
        self.assertTrue(second_candidates["cache_hit"])
        self.assertEqual(sum("GetBasicProductsList" in path for path in paths), 1)
        self.assertEqual(sum("InventoryBalance" in path for path in paths), 1)

    def test_invalid_response(self):
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"Status": "200"}))) as client:
            with self.assertRaises(InventoryResponseError):
                InventoryService(make_settings(), client, FakeAuthService()).search_inventory(item_code="ABC")

    def test_item_name_search_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "품목명 검색은 아직 지원하지 않습니다"):
            InventoryService(make_settings(), auth_service=FakeAuthService()).search_inventory(keyword="벤틀리")

    def test_item_code_is_normalized(self):
        with httpx.Client(transport=httpx.MockTransport(lambda request: success_response("ABC-123"))) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).get_inventory_by_item_code("abc-123")
        self.assertEqual(result["items"][0]["item_code"], "ABC-123")

    def test_low_stock_filter(self):
        with httpx.Client(transport=httpx.MockTransport(lambda request: success_response(quantity="9.5"))) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).get_low_stock_items("ABC", Decimal("10"))
        self.assertEqual(result["total"], 1)

    def test_limit_validation(self):
        for limit in (0, 201):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "200건 이하"):
                    InventoryService(make_settings(), auth_service=FakeAuthService()).search_inventory(item_code="ABC", limit=limit)

    def test_quantity_conversion(self):
        self.assertEqual(InventoryService.parse_quantity(12), Decimal("12"))
        self.assertEqual(InventoryService.parse_quantity("12.50"), Decimal("12.50"))
        self.assertEqual(InventoryService.parse_quantity("1,234"), Decimal("1234"))

    def test_invalid_quantity_is_not_silently_zeroed(self):
        with self.assertRaises(InventoryResponseError):
            InventoryService.parse_quantity("not-a-number", "SAFE-CODE")

    def test_sensitive_values_are_not_logged(self):
        auth = FakeAuthService()
        failure = httpx.Response(500, json={
            "Data": None, "Status": "500", "Error": {"Code": 0, "Message": "Check Parameter"},
        })
        with httpx.Client(transport=httpx.MockTransport(lambda request: failure)) as client:
            with self.assertLogs("app.services.inventory_service", logging.WARNING) as captured:
                with self.assertRaises(Exception):
                    InventoryService(make_settings(), client, auth).search_inventory(item_code="ABC")
        logs = " ".join(captured.output)
        self.assertNotIn(SESSION_ONE, logs)
        self.assertNotIn("private-cert-key", logs)

    def test_products_result_array(self):
        rows = [{"PROD_CD": "00016", "PROD_DES": "벤틀리", "SIZE_DES": "", "UNIT": "EA"}]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(item_code="00016")
        self.assertEqual(products[0]["item_name"], "벤틀리")
        self.assertEqual(products[0]["unit"], "EA")

    def test_product_search_does_not_force_product_type_zero(self):
        seen = {}

        def handler(request):
            seen.update(json.loads(request.content))
            return product_response([])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            InventoryService(make_settings(), client, FakeAuthService()).search_products(keyword="벤틀리")
        self.assertEqual(seen["PROD_TYPE"], "")

    def test_products_success_without_is_success_field(self):
        response = httpx.Response(200, json={
            "Data": {"TotalCnt": 1, "Result": [{"PROD_CD": "00016", "PROD_DES": "벤틀리"}]},
            "Status": "200", "Error": None,
        })
        with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(item_code="00016")
        self.assertEqual(products[0]["item_code"], "00016")

    def test_products_result_json_string(self):
        rows = [{"PROD_CD": "00016", "PROD_DES": "벤틀리"}]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows, True))) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(keyword="벤틀리")
        self.assertEqual([item["item_code"] for item in products], ["00016"])

    def test_product_name_partial_search_is_case_insensitive(self):
        rows = [
            {"PROD_CD": "A", "PROD_DES": "Bentley Parts"},
            {"PROD_CD": "B", "PROD_DES": "Other"},
        ]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(keyword="bEnTlEy")
        self.assertEqual([item["item_code"] for item in products], ["A"])

    def test_product_code_exact_match_is_preferred(self):
        rows = [
            {"PROD_CD": "ABC", "PROD_DES": "정확"},
            {"PROD_CD": "ABC-2", "PROD_DES": "부분"},
        ]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(item_code="abc")
        self.assertEqual([item["item_code"] for item in products], ["ABC"])

    def test_unknown_product_code_does_not_return_first_cached_product(self):
        rows = [
            {"PROD_CD": "ABC", "PROD_DES": "첫 번째 품목"},
            {"PROD_CD": "DEF", "PROD_DES": "두 번째 품목"},
        ]
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response(rows))) as client:
            products = InventoryService(make_settings(), client, FakeAuthService()).search_products(
                item_code="UNKNOWN",
            )
        self.assertEqual(products, [])

    def test_location_inventory_parsing_and_negative_quantity(self):
        rows = [{
            "WH_CD": "00001", "WH_DES": "본사", "PROD_CD": "00016",
            "PROD_DES": "벤틀리", "PROD_SIZE_DES": "벤틀리 / 기본", "BAL_QTY": "-3.0000000000",
        }]
        with httpx.Client(transport=httpx.MockTransport(lambda request: location_response(rows))) as client:
            locations = InventoryService(make_settings(), client, FakeAuthService()).get_inventory_by_location(item_code="00016")
        self.assertEqual(locations[0]["warehouse_name"], "본사")
        self.assertEqual(locations[0]["quantity"], Decimal("-3.0000000000"))

    def test_inventory_total_is_sum_of_warehouses(self):
        products = [{"PROD_CD": "00016", "PROD_DES": "벤틀리", "UNIT": "EA"}]
        locations = [
            {"WH_CD": "00001", "WH_DES": "본사", "PROD_CD": "00016", "BAL_QTY": "15"},
            {"WH_CD": "00002", "WH_DES": "파주", "PROD_CD": "00016", "BAL_QTY": "8"},
        ]

        def handler(request):
            return product_response(products) if "GetBasicProductsList" in request.url.path else location_response(locations)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).search_inventory_by_keyword("벤틀리")
        self.assertEqual(result["items"][0]["total_quantity"], Decimal("23"))
        self.assertEqual(len(result["items"][0]["warehouses"]), 2)

    def test_keyword_search_calls_product_lookup_only_once(self):
        products = [
            {"PROD_CD": "00016", "PROD_DES": "벤틀리 A"},
            {"PROD_CD": "00017", "PROD_DES": "벤틀리 B"},
        ]
        endpoint_calls = {"products": 0, "locations": 0}

        def handler(request):
            if "GetBasicProductsList" in request.url.path:
                endpoint_calls["products"] += 1
                return product_response(products)
            endpoint_calls["locations"] += 1
            code = json.loads(request.content)["PROD_CD"]
            return location_response([{
                "WH_CD": "00001", "WH_DES": "본사", "PROD_CD": code, "BAL_QTY": "1",
            }])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).search_inventory_by_keyword(
                "벤틀리", limit=10,
            )
        self.assertEqual(result["total"], 2)
        self.assertEqual(endpoint_calls, {"products": 1, "locations": 2})

    def test_product_not_found(self):
        with httpx.Client(transport=httpx.MockTransport(lambda request: product_response([]))) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).search_inventory_by_keyword("없는품목")
        self.assertEqual(result["total"], 0)

    def test_no_location_inventory_returns_zero_total(self):
        products = [{"PROD_CD": "00016", "PROD_DES": "벤틀리"}]

        def handler(request):
            return product_response(products) if "GetBasicProductsList" in request.url.path else location_response([])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = InventoryService(make_settings(), client, FakeAuthService()).get_aggregated_inventory("00016")
        self.assertEqual(result["items"][0]["total_quantity"], Decimal("0"))
        self.assertEqual(result["items"][0]["warehouses"], [])

    def test_korea_current_date_is_used_for_base_date(self):
        seen = {}

        def handler(request):
            seen.update(json.loads(request.content))
            return location_response([])

        with patch.object(InventoryService, "_korea_today", return_value="20260715"):
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                InventoryService(make_settings(), client, FakeAuthService()).get_inventory_by_location(item_code="00016")
        self.assertEqual(seen["BASE_DATE"], "20260715")

    def test_product_endpoint_session_expiration_retries_once(self):
        auth = FakeAuthService()
        calls = []

        def handler(request):
            calls.append(request.url.params["SESSION_ID"])
            if len(calls) == 1:
                return httpx.Response(401, json={
                    "Data": None, "Status": "401", "Error": {"Code": 401, "Message": "Session expired"},
                })
            return product_response([])

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            InventoryService(make_settings(), client, auth).search_products(keyword="벤틀리")
        self.assertEqual(auth.calls, [False, True])


class InventoryRouteTest(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    @staticmethod
    def safe_result():
        return {
            "success": True,
            "authenticated": True,
            "total": 1,
            "items": [{
                "item_code": "ABC", "item_name": "품목", "size": None, "unit": "EA",
                "total_quantity": Decimal("3.5"),
                "warehouses": [{"warehouse_code": "001", "warehouse_name": "본사", "quantity": Decimal("3.5")}],
            }],
            "message": "재고 조회에 성공했습니다.",
            "response_time_ms": 10,
        }

    def test_authenticated_inventory_search(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="사용자", password_hash="-", role="user",
        )
        with patch("app.api.routers.inventory.InventoryService") as service:
            service.return_value.get_aggregated_inventory.return_value = self.safe_result()
            response = TestClient(app).get("/inventory/search?item_code=ABC")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("SESSION_ID", response.text)

    def test_low_stock_analysis_endpoint_is_disabled_without_external_lookup(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="사용자", password_hash="-", role="user",
        )
        with patch("app.services.inventory_analysis_service.InventoryService") as service:
            response = TestClient(app).get(
                "/inventory/analyze?intent=inventory_low_stock&threshold=10"
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["analysis"]["disabled"])
        self.assertIn("일시 중지", response.json()["answer"])
        service.return_value.search_products.assert_not_called()
        service.return_value.get_inventory_by_location.assert_not_called()

    def test_rate_limit_is_safe_429(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="사용자", password_hash="-", role="user",
        )
        error = InventoryRateLimitError(
            "rate_limited", "이카운트 조회 요청이 잠시 제한되었습니다. 잠시 후 다시 조회해 주세요.", 412, "PRIVATE",
        )
        with patch("app.api.routers.inventory.InventoryService") as service:
            service.return_value.get_aggregated_inventory.side_effect = error
            response = TestClient(app).get("/inventory/search?item_code=ABC")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.json()["detail"]["message"],
            "이카운트 요청 제한으로 약 60초 후 다시 조회할 수 있습니다.",
        )
        self.assertEqual(response.json()["detail"]["retry_after_seconds"], 60)
        self.assertEqual(response.headers["retry-after"], "60")
        self.assertEqual(response.headers["x-inventory-error-code"], "ECOUNT_RATE_LIMITED")
        self.assertNotIn("PRIVATE", response.text)

    def test_unauthenticated_inventory_search_is_401(self):
        response = TestClient(app).get("/inventory/search?item_code=ABC")
        self.assertEqual(response.status_code, 401)

    def test_admin_inventory_endpoint_success(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, username="admin", name="관리자", password_hash="-", role="admin",
        )
        with patch("app.api.routers.ecount_integration.InventoryService") as service:
            service.return_value.get_aggregated_inventory.return_value = self.safe_result()
            response = TestClient(app).get("/admin/integrations/ecount/inventory/test?item_code=ABC")
        self.assertEqual(response.status_code, 200)

    def test_normal_user_admin_inventory_endpoint_is_403(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="사용자", password_hash="-", role="user",
        )
        response = TestClient(app).get("/admin/integrations/ecount/inventory/test?item_code=ABC")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
