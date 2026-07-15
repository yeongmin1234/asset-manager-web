import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import Settings, settings


logger = logging.getLogger(__name__)

# ECOUNT's detailed Open API manual is available only after ERP login.
# Verify these isolated mode-specific endpoints against that manual before enabling production.
ECOUNT_ENDPOINTS = {
    "test": {
        "zone": "https://sboapi.ecount.com/OAPI/V2/Zone",
        "login": "https://sboapi{zone}.ecount.com/OAPI/V2/OAPILogin",
    },
    "production": {
        "zone": "https://oapi.ecount.com/OAPI/V2/Zone",
        "login": "https://oapi{zone}.ecount.com/OAPI/V2/OAPILogin",
    },
}


class EcountApiError(Exception):
    def __init__(self, kind: str, message: str, http_status: Optional[int] = None, response_code: str = ""):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.http_status = http_status
        self.response_code = response_code


class EcountConfigurationError(EcountApiError):
    pass


class EcountTimeoutError(EcountApiError):
    pass


class EcountConnectionError(EcountApiError):
    pass


@dataclass
class EcountAuthResult:
    success: bool
    enabled: bool
    mode: str
    zone: str
    authenticated: bool
    message: str
    response_time_ms: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "enabled": self.enabled,
            "mode": self.mode,
            "zone": self.zone,
            "authenticated": self.authenticated,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
        }


class EcountApiService:
    def __init__(self, config: Settings = settings, client: Optional[httpx.Client] = None):
        self.config = config
        self._client = client

    def validate_settings(self) -> None:
        missing = (
            (self.config.ecount_company_code, "이카운트 회사코드가 설정되지 않았습니다."),
            (self.config.ecount_user_id, "이카운트 사용자 ID가 설정되지 않았습니다."),
            (self.config.ecount_api_cert_key, "이카운트 API 인증키가 설정되지 않았습니다."),
        )
        for value, message in missing:
            if not (value or "").strip():
                raise EcountConfigurationError("configuration", message)

    def get_zone(self) -> str:
        self.validate_settings()
        endpoint = ECOUNT_ENDPOINTS[self.config.ecount_api_mode]["zone"]
        payload = {"COM_CODE": self.config.ecount_company_code.strip()}
        data, status_code = self._post(endpoint, payload, "zone")
        if not self._is_success(data):
            self._raise_external("zone_failed", "이카운트 Zone 조회에 실패했습니다.", status_code, data)
        zone = self._read_value(data, "ZONE")
        if not zone:
            self._raise_external("invalid_zone_response", "이카운트 Zone 응답 형식이 올바르지 않습니다.", status_code, data)
        return str(zone).strip()

    def authenticate(self, zone: str) -> bool:
        self.validate_settings()
        normalized_zone = (zone or "").strip()
        if not normalized_zone or not normalized_zone.replace("-", "").isalnum():
            raise EcountApiError("invalid_zone_response", "이카운트 Zone 응답 형식이 올바르지 않습니다.")
        endpoint = ECOUNT_ENDPOINTS[self.config.ecount_api_mode]["login"].format(zone=normalized_zone.lower())
        payload = {
            "COM_CODE": self.config.ecount_company_code.strip(),
            "USER_ID": self.config.ecount_user_id.strip(),
            "API_CERT_KEY": self.config.ecount_api_cert_key.strip(),
            "LAN_TYPE": "ko-KR",
            "ZONE": normalized_zone,
        }
        data, status_code = self._post(endpoint, payload, "authentication")
        if not self._is_success(data):
            self._raise_external("authentication_failed", "이카운트 API 인증에 실패했습니다.", status_code, data)
        session_id = self._read_value(data, "SESSION_ID")
        if not session_id:
            self._raise_external("session_not_issued", "이카운트 SESSION_ID가 발급되지 않았습니다.", status_code, data)
        # SESSION_ID is intentionally reduced to a boolean and discarded here.
        return True

    def test_connection(self) -> EcountAuthResult:
        started_at = time.monotonic()
        if not self.config.ecount_enabled:
            return EcountAuthResult(
                success=False,
                enabled=False,
                mode=self.config.ecount_api_mode,
                zone="",
                authenticated=False,
                message="이카운트 API 연동이 비활성화되어 있습니다.",
                response_time_ms=self._elapsed_ms(started_at),
            )
        self.validate_settings()
        zone = self.get_zone()
        authenticated = self.authenticate(zone)
        return EcountAuthResult(
            success=authenticated,
            enabled=True,
            mode=self.config.ecount_api_mode,
            zone=zone,
            authenticated=authenticated,
            message="이카운트 API 인증에 성공했습니다.",
            response_time_ms=self._elapsed_ms(started_at),
        )

    def _post(self, url: str, payload: Dict[str, str], operation: str) -> Tuple[Dict[str, Any], int]:
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.Client(
                timeout=self.config.ecount_request_timeout,
                verify=self.config.ecount_trust_ssl,
            )
        try:
            response = client.post(url, json=payload)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                self._log_error("invalid_response", response.status_code)
                raise EcountApiError(
                    "invalid_response", "이카운트 API 응답 형식이 올바르지 않습니다.", response.status_code,
                ) from exc
            if not isinstance(data, dict):
                self._log_error("invalid_response", response.status_code)
                raise EcountApiError(
                    "invalid_response", "이카운트 API 응답 형식이 올바르지 않습니다.", response.status_code,
                )
            return data, response.status_code
        except httpx.TimeoutException as exc:
            self._log_error("timeout")
            raise EcountTimeoutError("timeout", "이카운트 API 응답 시간이 초과되었습니다.") from exc
        except httpx.HTTPStatusError as exc:
            self._log_error("{}_http_error".format(operation), exc.response.status_code)
            raise EcountConnectionError(
                "{}_http_error".format(operation), "이카운트 API 연결에 실패했습니다.", exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            self._log_error("connection_failed")
            raise EcountConnectionError("connection_failed", "이카운트 API 연결에 실패했습니다.") from exc
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def _read_value(data: Dict[str, Any], key: str) -> Any:
        nested = data.get("Data")
        if isinstance(nested, dict):
            if nested.get(key):
                return nested.get(key)
            nested_data = nested.get("Datas")
            if isinstance(nested_data, dict) and nested_data.get(key):
                return nested_data.get(key)
        return data.get(key)

    @classmethod
    def _is_success(cls, data: Dict[str, Any]) -> bool:
        status = data.get("Status")
        if isinstance(status, str):
            return status.upper() == "200"
        if isinstance(status, int):
            return status == 200
        code = cls._response_code(data)
        return code in ("", "0", "200", "SUCCESS")

    @staticmethod
    def _response_code(data: Dict[str, Any]) -> str:
        for container in (data, data.get("Error"), data.get("Errors")):
            if isinstance(container, dict):
                for key in ("Code", "CODE", "ErrorCode", "ERROR_CODE"):
                    value = container.get(key)
                    if value is not None:
                        return str(value)[:64]
        return ""

    def _raise_external(self, kind: str, message: str, http_status: int, data: Dict[str, Any]) -> None:
        code = self._response_code(data)
        self._log_error(kind, http_status, code)
        raise EcountApiError(kind, message, http_status, code)

    @staticmethod
    def _log_error(kind: str, http_status: Optional[int] = None, response_code: str = "") -> None:
        logger.warning(
            "ECOUNT API error kind=%s http_status=%s response_code=%s",
            kind,
            http_status if http_status is not None else "-",
            response_code or "-",
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((time.monotonic() - started_at) * 1000))
