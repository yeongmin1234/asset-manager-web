import logging
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import Settings, settings
from app.services.ecount_api_service import (
    EcountApiError,
    EcountApiService,
    EcountConfigurationError,
    EcountTimeoutError,
)


logger = logging.getLogger(__name__)
INVENTORY_ENDPOINT = (
    "https://oapi{zone}.ecount.com/OAPI/V2/InventoryBalance/"
    "ViewInventoryBalanceStatus"
)
PRODUCTS_ENDPOINT = (
    "https://oapi{zone}.ecount.com/OAPI/V2/InventoryBasic/"
    "GetBasicProductsList"
)
LOCATION_INVENTORY_ENDPOINT = (
    "https://oapi{zone}.ecount.com/OAPI/V2/InventoryBalance/"
    "GetListInventoryBalanceStatusByLocation"
)
MAX_RESULT_LIMIT = 200
MAX_LOW_STOCK_THRESHOLD = Decimal("1000000000")


class InventoryError(Exception):
    def __init__(self, kind: str, message: str, http_status: Optional[int] = None, response_code: str = ""):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.http_status = http_status
        self.response_code = response_code


class InventoryTimeoutError(InventoryError):
    pass


class InventoryConnectionError(InventoryError):
    pass


class InventoryResponseError(InventoryError):
    pass


class InventoryService:
    def __init__(
        self,
        config: Settings = settings,
        client: Optional[httpx.Client] = None,
        auth_service: Optional[EcountApiService] = None,
    ):
        self.config = config
        self._client = client
        self.auth_service = auth_service or EcountApiService(config=config, client=client)

    def search_inventory(
        self,
        keyword: Optional[str] = None,
        item_code: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        limit: int = 50,
        base_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        started_at = time.monotonic()
        if self.config.ecount_api_mode != "production":
            raise EcountConfigurationError(
                "unsupported_mode", "확인된 재고 API 규격은 production 모드만 지원합니다.",
            )
        normalized_code = self._validate_search(keyword, item_code, warehouse_code, limit, base_date)
        normalized_date = base_date or self._korea_today()
        payload = {
            "BASE_DATE": normalized_date,
            "PROD_CD": normalized_code,
            "ZERO_FLAG": "N",
            "BAL_FLAG": "N",
            "DEL_GUBUN": "N",
            "SAFE_FLAG": "N",
        }
        if warehouse_code:
            payload["WH_CD"] = warehouse_code.strip().upper()

        raw_items = self._fetch_with_single_reauthentication(payload)
        items = [self._normalize_item(item) for item in raw_items[:limit]]
        message = "재고 조회에 성공했습니다." if items else "검색 조건에 맞는 재고가 없습니다."
        elapsed = max(0, int((time.monotonic() - started_at) * 1000))
        logger.info("ECOUNT inventory query success count=%s response_time_ms=%s", len(items), elapsed)
        return {
            "success": True,
            "authenticated": True,
            "total": len(items),
            "items": items,
            "message": message,
            "response_time_ms": elapsed,
        }

    def search_products(
        self,
        keyword: Optional[str] = None,
        item_code: Optional[str] = None,
        product_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        self._validate_common_mode_and_limit(limit)
        normalized_code = (item_code or "").strip().upper()
        if len(normalized_code) > 20:
            raise ValueError("품목코드는 20자 이하로 입력해주세요.")
        payload = {
            "PROD_CD": normalized_code,
            "PROD_TYPE": (product_type or "").strip(),
        }
        raw_items = self._fetch_with_single_reauthentication(payload, PRODUCTS_ENDPOINT)
        products = [self._normalize_product(item) for item in raw_items]
        if normalized_code:
            exact = [item for item in products if item["item_code"].upper() == normalized_code]
            products = exact or products
        normalized_keyword = (keyword or "").strip().casefold()
        if normalized_keyword:
            products = [
                item for item in products
                if normalized_keyword in (item["item_name"] or "").casefold()
                or normalized_keyword in item["item_code"].casefold()
            ]
        return products[:limit]

    def get_inventory_by_location(
        self,
        base_date: Optional[str] = None,
        item_code: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        self._validate_common_mode_and_limit(limit)
        normalized_date = base_date or self._korea_today()
        self._validate_base_date(normalized_date)
        normalized_code = (item_code or "").strip().upper()
        if len(normalized_code) > 20:
            raise ValueError("품목코드는 20자 이하로 입력해주세요.")
        normalized_warehouse = (warehouse_code or "").strip().upper()
        if len(normalized_warehouse) > 5:
            raise ValueError("창고코드는 5자 이하로 입력해주세요.")
        payload = {
            "BASE_DATE": normalized_date,
            "WH_CD": normalized_warehouse,
            "PROD_CD": normalized_code,
            "BAL_FLAG": "N",
            "DEL_GUBUN": "N",
            "DEL_LOCATION_YN": "N",
        }
        raw_items = self._fetch_with_single_reauthentication(payload, LOCATION_INVENTORY_ENDPOINT)
        return [self._normalize_location_item(item) for item in raw_items[:limit]]

    def search_inventory_by_keyword(
        self,
        keyword: str,
        base_date: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        started_at = time.monotonic()
        normalized_keyword = (keyword or "").strip()
        if not normalized_keyword:
            raise ValueError("검색할 품목명 또는 품목코드를 입력해주세요.")
        products = self.search_products(keyword=normalized_keyword, limit=limit)
        items = []
        for product in products:
            locations = self.get_inventory_by_location(
                base_date=base_date,
                item_code=product["item_code"],
                warehouse_code=warehouse_code,
                limit=MAX_RESULT_LIMIT,
            )
            items.append(self._aggregate_inventory(product, locations))
        return self._aggregate_response(items, started_at)

    def get_aggregated_inventory(
        self,
        item_code: str,
        base_date: Optional[str] = None,
        warehouse_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        started_at = time.monotonic()
        products = self.search_products(item_code=item_code, limit=1)
        if not products:
            return self._aggregate_response([], started_at)
        locations = self.get_inventory_by_location(
            base_date=base_date,
            item_code=products[0]["item_code"],
            warehouse_code=warehouse_code,
            limit=MAX_RESULT_LIMIT,
        )
        return self._aggregate_response([self._aggregate_inventory(products[0], locations)], started_at)

    def get_aggregated_low_stock(
        self,
        keyword: Optional[str] = None,
        item_code: Optional[str] = None,
        threshold: Decimal = Decimal("10"),
        base_date: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        normalized_threshold = self._validate_threshold(threshold)
        if item_code:
            result = self.get_aggregated_inventory(item_code, base_date, warehouse_code)
        elif keyword:
            result = self.search_inventory_by_keyword(keyword, base_date, warehouse_code, limit)
        else:
            started_at = time.monotonic()
            locations = self.get_inventory_by_location(
                base_date=base_date,
                warehouse_code=warehouse_code,
                limit=MAX_RESULT_LIMIT,
            )
            grouped = {}
            for location in locations:
                grouped.setdefault(location["item_code"], []).append(location)
            items = []
            for code, item_locations in list(grouped.items())[:limit]:
                first = item_locations[0]
                product = {
                    "item_code": code,
                    "item_name": first["item_name"],
                    "size": first["product_size_description"],
                    "unit": None,
                }
                items.append(self._aggregate_inventory(product, item_locations))
            result = self._aggregate_response(items, started_at)
        result["items"] = [item for item in result["items"] if item["total_quantity"] <= normalized_threshold]
        result["total"] = len(result["items"])
        result["message"] = (
            "부족 재고 조회에 성공했습니다." if result["items"] else "기준 수량 이하의 재고가 없습니다."
        )
        return result

    def get_inventory_by_item_code(
        self, item_code: str, warehouse_code: Optional[str] = None, limit: int = 50,
    ) -> Dict[str, Any]:
        return self.search_inventory(item_code=item_code, warehouse_code=warehouse_code, limit=limit)

    def get_low_stock_items(
        self,
        item_code: str,
        threshold: Decimal = Decimal("10"),
        warehouse_code: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        normalized_threshold = self._validate_threshold(threshold)
        result = self.search_inventory(
            item_code=item_code,
            warehouse_code=warehouse_code,
            limit=limit,
        )
        result["items"] = [item for item in result["items"] if item["quantity"] <= normalized_threshold]
        result["total"] = len(result["items"])
        result["message"] = (
            "부족 재고 조회에 성공했습니다."
            if result["items"]
            else "기준 수량 이하의 재고가 없습니다."
        )
        return result

    def _fetch_with_single_reauthentication(
        self, payload: Dict[str, str], endpoint_template: str = INVENTORY_ENDPOINT,
    ) -> List[Dict[str, Any]]:
        session = self._get_session(False)
        data, http_status = self._request_once(
            session.zone, session.session_id, payload, endpoint_template,
        )
        if self._is_authentication_failure(data, http_status):
            self._log_error("session_expired", http_status, self._safe_error_code(data))
            session = self._get_session(True)
            data, http_status = self._request_once(
                session.zone, session.session_id, payload, endpoint_template,
            )
            if self._is_authentication_failure(data, http_status):
                code = self._safe_error_code(data)
                self._log_error("authentication_failed", http_status, code)
                raise InventoryError(
                    "authentication_failed", "이카운트 API 인증에 실패했습니다.", http_status, code,
                )
        return self._validate_response(data, http_status)

    def _get_session(self, force_refresh: bool):
        try:
            return self.auth_service.get_authenticated_session(force_refresh=force_refresh)
        except EcountConfigurationError:
            raise
        except EcountTimeoutError as exc:
            raise InventoryTimeoutError("authentication_timeout", "이카운트 재고 조회 시간이 초과되었습니다.") from exc
        except EcountApiError as exc:
            raise InventoryError("authentication_failed", "이카운트 API 인증에 실패했습니다.", exc.http_status, exc.response_code) from exc

    def _request_once(
        self,
        zone: str,
        session_id: str,
        payload: Dict[str, str],
        endpoint_template: str = INVENTORY_ENDPOINT,
    ) -> Tuple[Dict[str, Any], int]:
        endpoint = endpoint_template.format(zone=zone.lower())
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.Client(timeout=self.config.ecount_request_timeout, verify=self.config.ecount_trust_ssl)
        try:
            response = client.post(endpoint, params={"SESSION_ID": session_id}, json=payload)
            status_code = response.status_code
            try:
                data = response.json()
            except ValueError as exc:
                self._log_error("invalid_response", status_code)
                raise InventoryResponseError(
                    "invalid_response", "이카운트 재고 응답 형식을 확인할 수 없습니다.", status_code,
                ) from exc
            if not isinstance(data, dict):
                raise InventoryResponseError(
                    "invalid_response", "이카운트 재고 응답 형식을 확인할 수 없습니다.", status_code,
                )
            if status_code >= 400 and status_code not in (401, 403):
                self._log_error("http_error", status_code, self._safe_error_code(data))
                raise InventoryConnectionError(
                    "http_error", "이카운트 재고 API에 연결할 수 없습니다.", status_code,
                )
            return data, status_code
        except httpx.TimeoutException as exc:
            self._log_error("timeout")
            raise InventoryTimeoutError("timeout", "이카운트 재고 조회 시간이 초과되었습니다.") from exc
        except httpx.RequestError as exc:
            self._log_error("connection_failed")
            raise InventoryConnectionError("connection_failed", "이카운트 재고 API에 연결할 수 없습니다.") from exc
        finally:
            if owns_client:
                client.close()

    def _validate_response(self, data: Dict[str, Any], http_status: int) -> List[Dict[str, Any]]:
        payload = data.get("Data")
        if (
            data.get("Status") != "200"
            or not isinstance(payload, dict)
            or payload.get("IsSuccess") is False
        ):
            self._log_error("api_failure", http_status, self._safe_error_code(data))
            raise InventoryResponseError(
                "api_failure", "이카운트 재고 응답 형식을 확인할 수 없습니다.", http_status,
                self._safe_error_code(data),
            )
        result = payload.get("Result")
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (TypeError, ValueError) as exc:
                self._log_error("invalid_result_json", http_status)
                raise InventoryResponseError(
                    "invalid_result", "이카운트 재고 응답 형식을 확인할 수 없습니다.", http_status,
                ) from exc
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            self._log_error("invalid_result", http_status)
            raise InventoryResponseError(
                "invalid_result", "이카운트 재고 응답 형식을 확인할 수 없습니다.", http_status,
            )
        return result

    @staticmethod
    def _normalize_product(item: Dict[str, Any]) -> Dict[str, Any]:
        code = str(item.get("PROD_CD") or "").strip().upper()
        if not code:
            raise InventoryResponseError("missing_item_code", "이카운트 품목 응답 형식을 확인할 수 없습니다.")
        return {
            "item_code": code,
            "item_name": str(item.get("PROD_DES") or "").strip() or None,
            "size": str(item.get("SIZE_DES") or "").strip() or None,
            "unit": str(item.get("UNIT") or "").strip() or None,
            "product_type": str(item.get("PROD_TYPE") or "").strip() or None,
            "balance_managed": str(item.get("BAL_FLAG") or "").strip() or None,
            "class_code_1": str(item.get("CLASS_CD") or "").strip() or None,
            "class_code_2": str(item.get("CLASS_CD2") or "").strip() or None,
            "class_code_3": str(item.get("CLASS_CD3") or "").strip() or None,
            "barcode": str(item.get("BAR_CODE") or "").strip() or None,
        }

    def _normalize_location_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        code = str(item.get("PROD_CD") or "").strip().upper()
        if not code:
            raise InventoryResponseError("missing_item_code", "이카운트 창고별 재고 응답 형식을 확인할 수 없습니다.")
        return {
            "item_code": code,
            "item_name": str(item.get("PROD_DES") or "").strip() or None,
            "product_size_description": str(item.get("PROD_SIZE_DES") or "").strip() or None,
            "warehouse_code": str(item.get("WH_CD") or "").strip().upper() or None,
            "warehouse_name": str(item.get("WH_DES") or "").strip() or None,
            "quantity": self.parse_quantity(item.get("BAL_QTY"), code),
        }

    @staticmethod
    def _aggregate_inventory(product: Dict[str, Any], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        matching = [item for item in locations if item["item_code"] == product["item_code"]]
        warehouses = [
            {
                "warehouse_code": item["warehouse_code"],
                "warehouse_name": item["warehouse_name"],
                "quantity": item["quantity"],
            }
            for item in matching
        ]
        return {
            "item_code": product["item_code"],
            "item_name": product["item_name"],
            "size": product["size"],
            "unit": product["unit"],
            "total_quantity": sum((item["quantity"] for item in matching), Decimal("0")),
            "warehouses": warehouses,
        }

    @staticmethod
    def _aggregate_response(items: List[Dict[str, Any]], started_at: float) -> Dict[str, Any]:
        elapsed = max(0, int((time.monotonic() - started_at) * 1000))
        return {
            "success": True,
            "authenticated": True,
            "total": len(items),
            "items": items,
            "message": "재고 조회에 성공했습니다." if items else "검색 조건에 맞는 재고가 없습니다.",
            "response_time_ms": elapsed,
        }

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        code = str(item.get("PROD_CD") or "").strip().upper()
        if not code:
            raise InventoryResponseError("missing_item_code", "이카운트 재고 응답 형식을 확인할 수 없습니다.")
        return {
            "item_code": code,
            "item_name": None,
            "quantity": self.parse_quantity(item.get("BAL_QTY"), code),
            "warehouse_code": None,
            "warehouse_name": None,
            "unit": None,
            "updated_at": None,
        }

    @staticmethod
    def parse_quantity(value: Any, item_code: str = "") -> Decimal:
        if value is None or value == "":
            logger.warning("ECOUNT inventory invalid quantity item_code=%s reason=empty", item_code or "-")
            raise InventoryResponseError("invalid_quantity", "이카운트 재고 응답 형식을 확인할 수 없습니다.")
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, ValueError) as exc:
            logger.warning("ECOUNT inventory invalid quantity item_code=%s reason=not_numeric", item_code or "-")
            raise InventoryResponseError("invalid_quantity", "이카운트 재고 응답 형식을 확인할 수 없습니다.") from exc

    @staticmethod
    def _validate_search(keyword, item_code, warehouse_code, limit, base_date) -> str:
        if keyword and not item_code:
            raise ValueError("품목명 검색은 아직 지원하지 않습니다. 품목코드를 입력해주세요.")
        normalized_code = (item_code or "").strip().upper()
        if not normalized_code:
            raise ValueError("품목코드를 입력해주세요.")
        if len(normalized_code) > 20:
            raise ValueError("품목코드는 20자 이하로 입력해주세요.")
        if warehouse_code and len(warehouse_code.strip()) > 5:
            raise ValueError("창고코드는 5자 이하로 입력해주세요.")
        if limit < 1 or limit > MAX_RESULT_LIMIT:
            raise ValueError("조회 건수는 1건 이상 200건 이하로 입력해주세요.")
        if base_date:
            try:
                datetime.strptime(base_date, "%Y%m%d")
            except ValueError as exc:
                raise ValueError("기준일자는 YYYYMMDD 형식으로 입력해주세요.") from exc
        return normalized_code

    def _validate_common_mode_and_limit(self, limit: int) -> None:
        if self.config.ecount_api_mode != "production":
            raise EcountConfigurationError(
                "unsupported_mode", "확인된 재고 API 규격은 production 모드만 지원합니다.",
            )
        if limit < 1 or limit > MAX_RESULT_LIMIT:
            raise ValueError("조회 건수는 1건 이상 200건 이하로 입력해주세요.")

    @staticmethod
    def _validate_base_date(base_date: str) -> None:
        try:
            datetime.strptime(base_date, "%Y%m%d")
        except ValueError as exc:
            raise ValueError("기준일자는 YYYYMMDD 형식으로 입력해주세요.") from exc

    @staticmethod
    def _korea_today() -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y%m%d")

    @staticmethod
    def _validate_threshold(value: Decimal) -> Decimal:
        try:
            threshold = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("부족 재고 기준 수량이 올바르지 않습니다.") from exc
        if threshold < 0 or threshold > MAX_LOW_STOCK_THRESHOLD:
            raise ValueError("부족 재고 기준 수량이 허용 범위를 벗어났습니다.")
        return threshold

    @staticmethod
    def _is_authentication_failure(data: Dict[str, Any], http_status: int) -> bool:
        if http_status in (401, 403) or str(data.get("Status")) in ("401", "403"):
            return True
        error = data.get("Error")
        if not isinstance(error, dict):
            return False
        code = str(error.get("Code") or "").upper()
        message = str(error.get("Message") or "").lower()
        return code in ("401", "403", "AUTH", "UNAUTHORIZED") or any(
            token in message for token in (
                "session", "authentication", "login", "세션", "인증", "로그인",
            )
        )

    @staticmethod
    def _safe_error_code(data: Dict[str, Any]) -> str:
        error = data.get("Error")
        if isinstance(error, dict) and error.get("Code") is not None:
            return str(error.get("Code"))[:64]
        return ""

    @staticmethod
    def _log_error(kind: str, http_status: Optional[int] = None, response_code: str = "") -> None:
        logger.warning(
            "ECOUNT inventory error kind=%s http_status=%s response_code=%s",
            kind, http_status if http_status is not None else "-", response_code or "-",
        )
