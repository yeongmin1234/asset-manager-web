import logging
import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from app.schemas.asset import AssetOcrAnalysisResponse


logger = logging.getLogger(__name__)
SERIAL_NOT_FOUND_MESSAGE = (
    "이미지에서 시리얼번호를 찾지 못했습니다. "
    "라벨이 선명하게 보이도록 다시 촬영하거나 다시 업로드해 주세요."
)
_WARNED_RUNTIMES = set()

SERIAL_LABEL_PATTERN = re.compile(
    r"(?:SERIAL\s*(?:NUMBER|NO\.?|#)?|SER\.?\s*NO\.?|S\s*/\s*N|S\s*N)"
    r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9 \t-]{4,34})",
    re.IGNORECASE,
)
SERIAL_CANDIDATE_PATTERN = re.compile(
    r"\b(?=[A-Z0-9-]{6,30}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+(?:-[A-Z0-9]+)*\b"
)
MODEL_LABEL_PATTERN = re.compile(
    r"\b(?:MODEL\s*(?:NAME|NO\.?|NUMBER)?|MTM)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 \t-]{3,34})\b",
    re.IGNORECASE,
)
PRODUCT_NUMBER_LABEL_PATTERN = re.compile(
    r"\b(?:TYPE\s*(?:NUMBER|NO\.?)?|PRODUCT\s*(?:NUMBER|NO\.?)|P\s*/\s*N|PART\s*(?:NUMBER|NO\.?))"
    r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9 \t-]{3,34})\b",
    re.IGNORECASE,
)

MANUFACTURERS = ["Lenovo", "Dell", "HP", "ASUS", "Samsung", "LG", "Apple"]
PRODUCT_WORD_CASES = {
    "THINKPAD": "ThinkPad",
    "LATITUDE": "Latitude",
    "OPTIPLEX": "OptiPlex",
    "PROBOOK": "ProBook",
    "ELITEBOOK": "EliteBook",
    "GALAXY": "Galaxy",
    "BOOK": "Book",
    "MACBOOK": "MacBook",
    "AIR": "Air",
    "PRO": "Pro",
}
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
    if not serial_number and ocr_text:
        logger.info("Asset OCR did not find serial number. Raw text excerpt: %s", _raw_excerpt(ocr_text))

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
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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
        texts: List[str] = []
        for variant_name, variant_image in _build_ocr_variants(image, Image, ImageEnhance, ImageFilter, ImageOps):
            try:
                text = pytesseract.image_to_string(variant_image, lang="eng", config="--psm 6")
            except pytesseract.TesseractNotFoundError:
                raise
            except Exception as exc:
                logger.debug("Asset OCR variant failed (%s): %s", variant_name, exc)
                continue
            if text.strip():
                texts.append(text)
        return _merge_ocr_texts(texts)
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
    for _score, raw_value in _labeled_candidates(uppercase_text, SERIAL_LABEL_PATTERN):
        serial_number = _normalize_identifier(raw_value, allow_hyphen=True)
        if _is_serial_candidate(serial_number):
            return serial_number

    candidates = SERIAL_CANDIDATE_PATTERN.findall(uppercase_text)
    for candidate in candidates:
        serial_number = _normalize_identifier(candidate, allow_hyphen=True)
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
    for _score, raw_value in _labeled_candidates(uppercase_text, MODEL_LABEL_PATTERN):
        model_name = _normalize_identifier(raw_value, allow_hyphen=True)
        if 4 <= len(model_name) <= 30:
            return model_name
    return None


def _extract_product_number(text: str) -> Optional[str]:
    uppercase_text = text.upper()
    for _score, raw_value in _labeled_candidates(uppercase_text, PRODUCT_NUMBER_LABEL_PATTERN):
        product_number = _normalize_identifier(raw_value, allow_hyphen=True)
        if 4 <= len(product_number) <= 30:
            return product_number
    return None


def _is_serial_candidate(value: Optional[str]) -> bool:
    if not value:
        return False
    if re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        return False
    if not 6 <= len(value) <= 30:
        return False
    return bool(re.search(r"[A-Z]", value) and re.search(r"\d", value))


def _clean_serial(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalize_identifier(value: str, allow_hyphen: bool = False) -> str:
    normalized = str(value or "").upper()
    normalized = normalized.replace("—", "-").replace("–", "-")
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    normalized = re.sub(r"[^A-Z0-9\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts = [part for part in re.split(r"[\s-]+", normalized) if part]
    if not parts:
        return ""
    if allow_hyphen and len(parts) == 2 and _should_restore_hyphen(parts[0], parts[1]):
        return parts[0] + "-" + parts[1]
    joined = "".join(parts)
    if allow_hyphen and "-" in normalized:
        hyphen_parts = [part for part in normalized.split("-") if part]
        hyphen_parts = [re.sub(r"[^A-Z0-9]", "", part) for part in hyphen_parts]
        hyphen_parts = [part for part in hyphen_parts if part]
        if len(hyphen_parts) >= 2:
            return "-".join(hyphen_parts)
    return joined


def _should_restore_hyphen(first_part: str, second_part: str) -> bool:
    if not first_part or not second_part:
        return False
    if len(first_part) in {2, 3, 4} and len(second_part) >= 4:
        return True
    return False


def _normalize_text(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        normalized_line = re.sub(r"[ \t]+", " ", line).strip()
        if normalized_line:
            lines.append(normalized_line)
    return "\n".join(lines)


def _title_product(value: str) -> str:
    words = str(value or "").strip().split()
    normalized_words: List[str] = []
    for word in words:
        upper_word = word.upper()
        if upper_word in PRODUCT_WORD_CASES:
            normalized_words.append(PRODUCT_WORD_CASES[upper_word])
        elif any(character.isdigit() for character in word):
            normalized_words.append(upper_word)
        else:
            normalized_words.append(word[:1].upper() + word[1:].lower())
    return " ".join(normalized_words)


def _build_ocr_variants(image, image_module, enhance_module, filter_module, ops_module) -> List[Tuple[str, object]]:
    base_image = ops_module.exif_transpose(image).convert("RGB")
    grayscale_image = base_image.convert("L")
    enlarged_image = _resize_image(base_image, image_module, 2.5)
    enlarged_gray = enlarged_image.convert("L")
    contrast_image = enhance_module.Contrast(enlarged_gray).enhance(2.0)
    sharp_image = contrast_image.filter(filter_module.SHARPEN)
    bright_image = enhance_module.Brightness(contrast_image).enhance(1.15)
    threshold_image = contrast_image.point(lambda pixel: 255 if pixel > 145 else 0)
    return [
        ("original", base_image),
        ("enlarged", enlarged_image),
        ("grayscale", grayscale_image),
        ("contrast", contrast_image),
        ("sharpen", sharp_image),
        ("brightness", bright_image),
        ("threshold", threshold_image),
    ]


def _resize_image(image, image_module, scale: float):
    width, height = image.size
    resampling = getattr(getattr(image_module, "Resampling", image_module), "LANCZOS")
    return image.resize((max(1, int(width * scale)), max(1, int(height * scale))), resampling)


def _merge_ocr_texts(texts: List[str]) -> str:
    seen = set()
    merged_lines: List[str] = []
    for text in texts:
        for line in text.splitlines():
            normalized_line = re.sub(r"[ \t]+", " ", line).strip()
            dedupe_key = normalized_line.upper()
            if not normalized_line or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            merged_lines.append(normalized_line)
    return "\n".join(merged_lines)


def _labeled_candidates(text: str, pattern: re.Pattern) -> List[Tuple[int, str]]:
    candidates: List[Tuple[int, str]] = []
    for match in pattern.finditer(text):
        raw_value = match.group(1)
        score = 100
        if "-" in raw_value:
            score += 10
        candidates.append((score, raw_value))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates


def _raw_excerpt(text: str) -> str:
    excerpt = re.sub(r"\s+", " ", text).strip()
    return excerpt[:500]


def _log_runtime_warning_once(runtime_name: str, message: str, exc: Exception) -> None:
    if runtime_name in _WARNED_RUNTIMES:
        return
    _WARNED_RUNTIMES.add(runtime_name)
    logger.warning("%s Detail: %s", message, exc)
