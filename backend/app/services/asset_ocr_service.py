import logging
import re
from io import BytesIO
from typing import Dict, List, Optional

from app.schemas.asset import AssetOcrAnalysisResponse


logger = logging.getLogger(__name__)
SERIAL_NOT_FOUND_MESSAGE = (
    "이미지에서 시리얼번호를 찾지 못했습니다. "
    "라벨이 선명하게 보이도록 다시 촬영하거나 다시 업로드해 주세요."
)
_WARNED_RUNTIMES = set()

SERIAL_LABEL_PATTERN = re.compile(
    r"(?:S\s*/\s*N|S\s*N|SERIAL\s*(?:NO|NUMBER)?|SER\.?\s*NO\.?)"
    r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{5,29})",
    re.IGNORECASE,
)
SERIAL_CANDIDATE_PATTERN = re.compile(r"\b(?=[A-Z0-9]{6,30}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b")
MODEL_LABEL_PATTERN = re.compile(
    r"\b(?:MODEL|MODEL\s*NO|MTM)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,29})\b",
    re.IGNORECASE,
)
PRODUCT_NUMBER_LABEL_PATTERN = re.compile(
    r"\b(?:TYPE|PRODUCT\s*(?:NO|NUMBER)|P/N|PART\s*(?:NO|NUMBER))"
    r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,29})\b",
    re.IGNORECASE,
)

MANUFACTURERS = ["Lenovo", "Dell", "HP", "ASUS", "Samsung", "LG", "Apple"]
PRODUCT_PATTERNS = [
    re.compile(r"\b(ThinkPad\s+[A-Z0-9][A-Z0-9\s-]{1,24})\b", re.IGNORECASE),
    re.compile(r"\b(Latitude\s+[A-Z0-9][A-Z0-9\s-]{1,24})\b", re.IGNORECASE),
    re.compile(r"\b(OptiPlex\s+[A-Z0-9][A-Z0-9\s-]{1,24})\b", re.IGNORECASE),
    re.compile(r"\b(ProBook\s+[A-Z0-9][A-Z0-9\s-]{1,24})\b", re.IGNORECASE),
    re.compile(r"\b(EliteBook\s+[A-Z0-9][A-Z0-9\s-]{1,24})\b", re.IGNORECASE),
    re.compile(r"\b(Galaxy\s+Book\s+[A-Z0-9][A-Z0-9\s-]{0,24})\b", re.IGNORECASE),
    re.compile(r"\b(MacBook(?:\s+(?:Air|Pro))?(?:\s+[A-Z0-9][A-Z0-9\s-]{0,16})?)\b", re.IGNORECASE),
]


def analyze_asset_image(image_bytes: bytes) -> AssetOcrAnalysisResponse:
    ocr_text = _read_text_with_tesseract(image_bytes)
    fields = _extract_fields(ocr_text)

    serial_number = fields.get("serial_number")
    source = "ocr" if serial_number or fields.get("product_name") or fields.get("model_name") else None
    message = "분석이 완료되었습니다." if serial_number else SERIAL_NOT_FOUND_MESSAGE

    return AssetOcrAnalysisResponse(
        product_name=fields.get("product_name"),
        manufacturer=fields.get("manufacturer"),
        model_name=fields.get("model_name"),
        product_number=fields.get("product_number"),
        serial_number=serial_number,
        source=source,
        message=message,
        raw_text=ocr_text[:2000] if ocr_text else None,
    )


def _read_text_with_tesseract(image_bytes: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        _log_runtime_warning_once(
            "tesseract-python",
            "Asset OCR skipped: Pillow or pytesseract package is not available.",
            exc,
        )
        return ""
    except Exception as exc:
        _log_runtime_warning_once(
            "tesseract",
            "Asset OCR skipped: Tesseract OCR runtime failed to initialize.",
            exc,
        )
        return ""

    try:
        image = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(image, lang="eng")
    except pytesseract.TesseractNotFoundError as exc:
        _log_runtime_warning_once(
            "tesseract",
            "Asset OCR skipped: tesseract executable was not found on this server.",
            exc,
        )
        return ""
    except Exception as exc:
        logger.warning("Asset OCR failed while reading image with Tesseract: %s", exc)
        return ""


def _extract_fields(text: str) -> Dict[str, Optional[str]]:
    normalized_text = _normalize_text(text)
    return {
        "serial_number": _extract_serial_number(normalized_text),
        "product_name": _extract_product_name(normalized_text),
        "manufacturer": _extract_manufacturer(normalized_text),
        "model_name": _extract_model_name(normalized_text),
        "product_number": _extract_product_number(normalized_text),
    }


def _extract_serial_number(text: str) -> Optional[str]:
    uppercase_text = text.upper()
    for match in SERIAL_LABEL_PATTERN.finditer(uppercase_text):
        serial_number = _clean_serial(match.group(1))
        if _is_serial_candidate(serial_number):
            return serial_number

    candidates = SERIAL_CANDIDATE_PATTERN.findall(uppercase_text)
    for candidate in candidates:
        serial_number = _clean_serial(candidate)
        if _is_serial_candidate(serial_number):
            return serial_number
    return None


def _extract_manufacturer(text: str) -> Optional[str]:
    for manufacturer in MANUFACTURERS:
        if re.search(r"\b" + re.escape(manufacturer) + r"\b", text, re.IGNORECASE):
            return manufacturer
    return None


def _extract_product_name(text: str) -> Optional[str]:
    for pattern in PRODUCT_PATTERNS:
        match = pattern.search(text)
        if match:
            return _title_product(match.group(1))
    return None


def _extract_model_name(text: str) -> Optional[str]:
    uppercase_text = text.upper()
    match = MODEL_LABEL_PATTERN.search(uppercase_text)
    if match:
        model_name = _clean_serial(match.group(1))
        if 4 <= len(model_name) <= 30:
            return model_name
    return None


def _extract_product_number(text: str) -> Optional[str]:
    uppercase_text = text.upper()
    match = PRODUCT_NUMBER_LABEL_PATTERN.search(uppercase_text)
    if match:
        product_number = _clean_serial(match.group(1))
        if 4 <= len(product_number) <= 30:
            return product_number
    return None


def _is_serial_candidate(value: Optional[str]) -> bool:
    if not value:
        return False
    if re.fullmatch(r"[A-Z0-9]{6,30}", value) is None:
        return False
    return bool(re.search(r"[A-Z]", value) and re.search(r"\d", value))


def _clean_serial(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


def _title_product(value: str) -> str:
    words = str(value or "").strip().split()
    normalized_words: List[str] = []
    for word in words:
        upper_word = word.upper()
        if upper_word in {"HP", "LG", "ASUS"}:
            normalized_words.append(upper_word)
        elif any(character.isdigit() for character in word):
            normalized_words.append(upper_word)
        else:
            normalized_words.append(word[:1].upper() + word[1:].lower())
    return " ".join(normalized_words)


def _log_runtime_warning_once(runtime_name: str, message: str, exc: Exception) -> None:
    if runtime_name in _WARNED_RUNTIMES:
        return
    _WARNED_RUNTIMES.add(runtime_name)
    logger.warning("%s Detail: %s", message, exc)
