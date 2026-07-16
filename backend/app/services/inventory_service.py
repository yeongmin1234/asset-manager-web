import logging
import json
import time
import copy
import threading
import re
import math
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
from app.services.product_match_service import prepare_product_search_fields, rank_product_matches


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
DEFAULT_RECOMMENDATION_LIMIT = 8
MAX_RECOMMENDATION_LIMIT = 10
INVENTORY_QUERY_CACHE_TTL_SECONDS = 60.0
INVENTORY_RATE_LIMIT_COOLDOWN_SECONDS = 60
PRODUCT_MASTER_CACHE_TTL_SECONDS = 3600.0
PRODUCT_MASTER_STALE_TTL_SECONDS = 86400.0
INVENTORY_QUERY_CACHE_MAX_ITEMS = 256
_query_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_rate_limit_until = 0.0
_product_master_cache: Dict[str, Tuple[float, float, List[Dict[str, Any]]]] = {}
_query_cache_lock = threading.Lock()
_external_request_lock = threading.Lock()
_product_master_lock = threading.Lock()


class InventoryError(Exception):
    def __init__(
        self,
        kind: str,
        message: str,
        http_status: Optional[int] = None,
        response_code: str = "",
        retry_after_seconds: Optional[int] = None,
    ):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.http_status = http_status
        self.response_code = response_code
        self.retry_after_seconds = retry_after_seconds


class InventoryTimeoutError(InventoryError):
    pass


class InventoryConnectionError(InventoryError):
    pass


class InventoryRateLimitError(InventoryError):
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
        products, _ = self._search_products_with_cache_status(
            keyword=keyword,
            item_code=item_code,
            product_type=product_type,
            limit=limit,
        )
        return products

    def list_products(
        self,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        product_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return product-master data only; this method never requests inventory data."""
        if page < 1:
            raise ValueError("페이지는 1 이상이어야 합니다.")
        if page_size < 1 or page_size > 100:
            raise ValueError("페이지 크기는 100건 이하이어야 합니다.")
        self._validate_common_mode_and_limit(page_size)
        products, cache_status = self._get_product_master(product_type)
        all_products = products
        normalized_keyword = self._normalize_product_search_text(keyword)
        if normalized_keyword:
            ranked = []
            for index, item in enumerate(products):
                priority = self._product_search_priority(item, normalized_keyword)
                if priority is not None:
                    ranked.append((priority, index, item))
            ranked.sort(key=lambda match: (match[0], match[1]))
            products = [match[2] for match in ranked]
            match_type = "standard"
            if not products:
                fuzzy = rank_product_matches(all_products, keyword, 8)
                products = fuzzy["items"]
                match_type = fuzzy["match_type"]
        else:
            match_type = "all"

        total = len(products)
        start = (page - 1) * page_size
        items = [
            {
                "item_code": item["item_code"],
                "item_name": item.get("item_name"),
                "size": item.get("size"),
                "unit": item.get("unit"),
            }
            for item in products[start:start + page_size]
        ]
        logger.info(
            "ECOUNT product list cache_hit=%s candidate_count=%s external_inventory_call=false",
            cache_status,
            total,
        )
        return {
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
            "data_source": "product_master_cache",
            "match_type": match_type,
        }

    def _search_products_with_cache_status(
        self,
        keyword: Optional[str] = None,
        item_code: Optional[str] = None,
        product_type: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], str]:
        self._validate_common_mode_and_limit(limit)
        normalized_code = (item_code or "").strip().upper()
        if len(normalized_code) > 20:
            raise ValueError("품목코드는 20자 이하로 입력해주세요.")
        products, cache_status = self._get_product_master(product_type)
        if normalized_code:
            exact = [item for item in products if item["item_code"].upper() == normalized_code]
            products = exact
        normalized_keyword = self._normalize_product_search_text(keyword)
        if normalized_keyword:
            products = [
                item for item in products
                if self._product_search_priority(item, normalized_keyword) is not None
            ]
        products = products[:limit]
        logger.info(
            "ECOUNT product search intent=product_search cache_hit=%s candidate_count=%s external_inventory_call=false",
            cache_status,
            len(products),
        )
        return products, cache_status

    def search_products_for_keywords(
        self,
        keywords: List[str],
        product_type: Optional[str] = None,
        limit_per_keyword: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        self._validate_common_mode_and_limit(min(MAX_RESULT_LIMIT, max(1, limit_per_keyword)))
        products, cache_status = self._get_product_master(product_type)
        result = {}
        for keyword in keywords[:10]:
            normalized = (keyword or "").strip().casefold()
            if not normalized:
                result[keyword] = []
                continue
            exact = [item for item in products if item["item_code"].casefold() == normalized]
            partial = [
                item for item in products
                if normalized in (item["item_name"] or "").casefold()
                or normalized in item["item_code"].casefold()
            ]
            result[keyword] = (exact or partial)[:limit_per_keyword]
        logger.info(
            "ECOUNT product search intent=product_compare cache_hit=%s candidate_count=%s external_inventory_call=false",
            cache_status,
            sum(len(items) for items in result.values()),
        )
        return result

    def recommend_products(self, keyword: str, limit: int = DEFAULT_RECOMMENDATION_LIMIT) -> Dict[str, Any]:
        normalized = (keyword or "").strip()
        if not normalized:
            raise ValueError("추천 품목 검색어를 입력해주세요.")
        if limit < 1 or limit > MAX_RECOMMENDATION_LIMIT:
            raise ValueError("추천 품목은 최대 10개까지 조회할 수 있습니다.")
        products, cache_status = self._get_product_master()
        matches = rank_product_matches(products, normalized, min(limit, DEFAULT_RECOMMENDATION_LIMIT))
        items = matches["items"]
        logger.info(
            "ECOUNT product recommendation match_type=%s candidate_count=%s highest_score=%s cache_hit=%s external_inventory_call=false",
            matches["match_type"], matches["total"], matches["highest_score"], cache_status,
        )
        return {
            "mode": "recommendation",
            "query": normalized,
            "total": matches["total"],
            "items": items,
            "has_more": matches["total"] > len(items),
            "limit": limit,
            "cache_hit": cache_status != "false",
            "match_type": matches["match_type"],
            "highest_score": matches["highest_score"],
        }

    def _get_product_master(
        self, product_type: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        cache_key = (product_type or "").strip()
        now = time.monotonic()
        with _product_master_lock:
            cached = _product_master_cache.get(cache_key)
            if cached is not None and cached[0] > now:
                return copy.deepcopy(cached[2]), "true"

            stale = cached if cached is not None and cached[1] > now else None
            payload = {"PROD_CD": "", "PROD_TYPE": cache_key}
            try:
                raw_items = self._fetch_with_single_reauthentication(payload, PRODUCTS_ENDPOINT)
            except InventoryRateLimitError:
                if stale is not None:
                    logger.warning(
                        "ECOUNT product master refresh rate_limited stale_cache_used=true candidate_count=%s",
                        len(stale[2]),
                    )
                    return copy.deepcopy(stale[2]), "stale"
                raise

            products = [self._normalize_product(item) for item in raw_items]
            cached_at = time.monotonic()
            _product_master_cache[cache_key] = (
                cached_at + PRODUCT_MASTER_CACHE_TTL_SECONDS,
                cached_at + PRODUCT_MASTER_STALE_TTL_SECONDS,
                copy.deepcopy(products),
            )
            return products, "false"

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
        product: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        started_at = time.monotonic()
        products = [product] if product else self.search_products(item_code=item_code, limit=1)
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
        cache_key = self._cache_key(endpoint_template, payload)
        enforce_inventory_cooldown = endpoint_template != PRODUCTS_ENDPOINT
        cached = self._get_cached_result(cache_key, enforce_inventory_cooldown)
        if cached is not None:
            return cached
        # Serialize cache misses in this Backend process. A second identical
        # request rechecks the cache after the first external request finishes.
        with _external_request_lock:
            cached = self._get_cached_result(cache_key, enforce_inventory_cooldown)
            if cached is not None:
                return cached
            logger.info(
                "ECOUNT request intent=%s product_search_cache_hit=false candidate_count=- external_inventory_call=%s",
                "inventory_lookup" if enforce_inventory_cooldown else "product_master_refresh",
                str(enforce_inventory_cooldown).lower(),
            )
            try:
                result = self._fetch_uncached_with_single_reauthentication(payload, endpoint_template)
            except InventoryRateLimitError as exc:
                if enforce_inventory_cooldown:
                    global _rate_limit_until
                    with _query_cache_lock:
                        now = time.monotonic()
                        _rate_limit_until = max(
                            _rate_limit_until,
                            now + INVENTORY_RATE_LIMIT_COOLDOWN_SECONDS,
                        )
                        exc.retry_after_seconds = max(
                            1, int(math.ceil(_rate_limit_until - now)),
                        )
                raise
            self._store_cached_result(cache_key, result)
            return copy.deepcopy(result)

    def _fetch_uncached_with_single_reauthentication(
        self, payload: Dict[str, str], endpoint_template: str,
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

    @staticmethod
    def _cache_key(endpoint_template: str, payload: Dict[str, str]) -> str:
        return endpoint_template + "|" + json.dumps(payload, sort_keys=True, ensure_ascii=True)

    @staticmethod
    def _get_cached_result(
        cache_key: str, enforce_inventory_cooldown: bool = True,
    ) -> Optional[List[Dict[str, Any]]]:
        now = time.monotonic()
        with _query_cache_lock:
            cached = _query_cache.get(cache_key)
            if cached is not None and cached[0] > now:
                return copy.deepcopy(cached[1])
            if cached is not None:
                _query_cache.pop(cache_key, None)
            if enforce_inventory_cooldown and _rate_limit_until > now:
                remaining = max(1, int(math.ceil(_rate_limit_until - now)))
                logger.warning(
                    "ECOUNT inventory request blocked kind=rate_limited remaining_seconds=%s external_inventory_call=false",
                    remaining,
                )
                raise InventoryRateLimitError(
                    "rate_limited",
                    "이카운트 조회 제한으로 잠시 후 다시 조회할 수 있습니다.",
                    412,
                    retry_after_seconds=remaining,
                )
            return None

    @staticmethod
    def _store_cached_result(cache_key: str, result: List[Dict[str, Any]]) -> None:
        now = time.monotonic()
        with _query_cache_lock:
            expired = [key for key, value in _query_cache.items() if value[0] <= now]
            for key in expired:
                _query_cache.pop(key, None)
            if len(_query_cache) >= INVENTORY_QUERY_CACHE_MAX_ITEMS:
                _query_cache.pop(next(iter(_query_cache)), None)
            _query_cache[cache_key] = (
                now + INVENTORY_QUERY_CACHE_TTL_SECONDS,
                copy.deepcopy(result),
            )

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
            if status_code == 412:
                safe_code = ""
                try:
                    limited_data = response.json()
                    if isinstance(limited_data, dict):
                        safe_code = self._safe_error_code(limited_data)
                except ValueError:
                    pass
                self._log_error("rate_limited", status_code, safe_code)
                raise InventoryRateLimitError(
                    "rate_limited",
                    "이카운트 조회 제한으로 잠시 후 다시 조회할 수 있습니다.",
                    status_code,
                    safe_code,
                    INVENTORY_RATE_LIMIT_COOLDOWN_SECONDS,
                )
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
        product = {
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
            "group_name_1": str(item.get("CLASS_DES") or "").strip() or None,
            "group_name_2": str(item.get("CLASS_DES2") or "").strip() or None,
            "group_name_3": str(item.get("CLASS_DES3") or "").strip() or None,
            "search_text": str(item.get("SEARCH_DES") or item.get("PROD_SEARCH") or "").strip() or None,
        }
        product["_search"] = prepare_product_search_fields(product)
        return product

    @staticmethod
    def _normalize_product_search_text(value: Any) -> str:
        return re.sub(r"\s+", "", str(value or "").strip()).casefold()

    @classmethod
    def _product_search_priority(cls, item: Dict[str, Any], keyword: str) -> Optional[int]:
        code = cls._normalize_product_search_text(item.get("item_code"))
        name = cls._normalize_product_search_text(item.get("item_name"))
        size = cls._normalize_product_search_text(item.get("size"))
        barcode = cls._normalize_product_search_text(item.get("barcode"))
        if code == keyword:
            return 0
        if name == keyword:
            return 1
        if name.startswith(keyword):
            return 2
        if keyword in name:
            return 3
        if keyword in size:
            return 4
        if barcode == keyword or keyword in barcode:
            return 5
        auxiliary_fields = (
            "search_text", "group_name_1", "group_name_2", "group_name_3",
            "class_code_1", "class_code_2", "class_code_3",
        )
        if any(keyword in cls._normalize_product_search_text(item.get(field)) for field in auxiliary_fields):
            return 6
        if keyword in code:
            return 7
        return None

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
            "item_name": product.get("item_name"),
            "size": product.get("size"),
            "unit": product.get("unit"),
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


def clear_inventory_query_cache() -> None:
    """Clear short-lived data/rate-limit caches without touching SESSION_ID."""
    global _rate_limit_until
    with _query_cache_lock:
        _query_cache.clear()
        _rate_limit_until = 0.0
    with _product_master_lock:
        _product_master_cache.clear()
