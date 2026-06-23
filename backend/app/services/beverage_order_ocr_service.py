import logging
import re
from io import BytesIO
from typing import List, Optional, Tuple

from app.schemas.beverage_order_record import BeverageOrderAmountOcrResponse


logger = logging.getLogger(__name__)
_WARNED_RUNTIMES = set()

AMOUNT_FOUND_MESSAGE = "이미지에서 결제금액을 자동 인식했습니다."
AMOUNT_NOT_FOUND_MESSAGE = "이미지에서 결제금액을 찾지 못했습니다. 금액을 직접 입력해 주세요."

PRIMARY_AMOUNT_KEYWORDS = [
    "총 결제금액",
    "총 결제 금액",
    "총결제금액",
    "최종 결제금액",
    "최종 결제 금액",
]

AMOUNT_KEYWORDS = [
    *PRIMARY_AMOUNT_KEYWORDS,
    "총 결제금액",
    "총 결제 금액",
    "결제 예정 금액",
    "결제금액",
    "결제 금액",
    "주문금액",
    "주문 금액",
    "합계",
    "총액",
]

AMOUNT_PATTERN = re.compile(
    r"(?:₩|￦)?\s*(\d{1,3}(?:(?:\s*,\s*|\s+)\d{3})+|\d{4,9})\s*(?:원)?"
)


def analyze_beverage_order_amount(image_bytes: bytes) -> BeverageOrderAmountOcrResponse:
    raw_text = _read_text_with_tesseract(image_bytes)
    candidates = _extract_amount_candidates(raw_text)
    amount = candidates[0] if candidates else None
    if amount is None and raw_text:
        logger.info("Beverage amount OCR did not find amount. Raw text excerpt: %s", _raw_excerpt(raw_text))

    return BeverageOrderAmountOcrResponse(
        amount=amount,
        amount_text=_format_amount_text(amount),
        candidates=candidates,
        message=AMOUNT_FOUND_MESSAGE if amount is not None else AMOUNT_NOT_FOUND_MESSAGE,
    )


def _read_text_with_tesseract(image_bytes: bytes) -> str:
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        import pytesseract
    except ImportError as exc:
        _log_runtime_warning_once(
            "tesseract-python",
            "Beverage amount OCR skipped: Pillow or pytesseract package is not available.",
            exc,
        )
        return ""
    except Exception as exc:
        _log_runtime_warning_once(
            "tesseract",
            "Beverage amount OCR skipped: Tesseract OCR runtime failed to initialize.",
            exc,
        )
        return ""

    try:
        image = Image.open(BytesIO(image_bytes))
        texts: List[str] = []
        for variant_name, variant_image in _build_ocr_variants(image, Image, ImageEnhance, ImageFilter, ImageOps):
            try:
                text = _image_to_string(pytesseract, variant_image)
            except pytesseract.TesseractNotFoundError:
                raise
            except Exception as exc:
                logger.debug("Beverage amount OCR variant failed (%s): %s", variant_name, exc)
                continue
            if text.strip():
                texts.append(text)
        return _merge_ocr_texts(texts)
    except pytesseract.TesseractNotFoundError as exc:
        _log_runtime_warning_once(
            "tesseract",
            "Beverage amount OCR skipped: tesseract executable was not found on this server.",
            exc,
        )
        return ""
    except Exception as exc:
        logger.warning("Beverage amount OCR failed while reading image with Tesseract: %s", exc)
        return ""


def _image_to_string(pytesseract_module, image) -> str:
    try:
        return pytesseract_module.image_to_string(image, lang="kor+eng", config="--psm 6")
    except pytesseract_module.TesseractError as exc:
        logger.debug("Beverage amount OCR kor+eng failed, retrying eng only: %s", exc)
        return pytesseract_module.image_to_string(image, lang="eng", config="--psm 6")


def _build_ocr_variants(image, image_module, enhance_module, filter_module, ops_module) -> List[Tuple[str, object]]:
    base_image = ops_module.exif_transpose(image).convert("RGB")
    grayscale_image = base_image.convert("L")
    enlarged_image = _resize_image(base_image, image_module, 2.0)
    enlarged_gray = enlarged_image.convert("L")
    contrast_image = enhance_module.Contrast(enlarged_gray).enhance(1.8)
    sharp_image = contrast_image.filter(filter_module.SHARPEN)
    bright_image = enhance_module.Brightness(contrast_image).enhance(1.12)
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


def _extract_amount_candidates(text: str) -> List[int]:
    primary_keyword_amounts = _extract_primary_keyword_amounts(text)
    keyword_amounts = _extract_keyword_amounts(text)
    all_amounts = _extract_all_amounts(text)
    ordered_amounts = primary_keyword_amounts[:]
    for amount in keyword_amounts:
        if amount not in ordered_amounts:
            ordered_amounts.append(amount)
    for amount in sorted(all_amounts, reverse=True):
        if amount not in ordered_amounts:
            ordered_amounts.append(amount)
    return ordered_amounts


def _extract_primary_keyword_amounts(text: str) -> List[int]:
    lines = _normalize_ocr_lines(text)
    amounts: List[int] = []
    for index, line in enumerate(lines):
        if not _contains_primary_amount_keyword(line):
            continue
        window_start = max(0, index - 2)
        window_end = min(len(lines), index + 4)
        ordered_lines = [line]
        ordered_lines.extend(lines[index + 1:window_end])
        ordered_lines.extend(lines[window_start:index])
        for amount in _extract_all_amounts("\n".join(ordered_lines)):
            if amount not in amounts:
                amounts.append(amount)
    if amounts:
        logger.debug(
            "Beverage amount OCR matched primary payment keyword. Candidates: %s",
            amounts[:3],
        )
    return amounts


def _extract_keyword_amounts(text: str) -> List[int]:
    amounts: List[int] = []
    normalized_text = str(text or "")
    for keyword in AMOUNT_KEYWORDS:
        for match in re.finditer(re.escape(keyword), normalized_text, re.IGNORECASE):
            nearby_text = normalized_text[match.start():match.end() + 140]
            for amount in _extract_all_amounts(nearby_text):
                if amount not in amounts:
                    amounts.append(amount)
    return amounts


def _extract_all_amounts(text: str) -> List[int]:
    amounts: List[int] = []
    for match in AMOUNT_PATTERN.finditer(str(text or "")):
        amount = _normalize_amount(match.group(1))
        if amount is None:
            continue
        if amount not in amounts:
            amounts.append(amount)
    return amounts


def _normalize_amount(value: str) -> Optional[int]:
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    if not digits:
        return None
    amount = int(digits)
    if amount <= 0:
        return None
    return amount


def _normalize_ocr_lines(text: str) -> List[str]:
    lines: List[str] = []
    for line in str(text or "").splitlines():
        normalized_line = re.sub(r"[ \t]+", " ", line).strip()
        if normalized_line:
            lines.append(normalized_line)
    return lines


def _contains_primary_amount_keyword(line: str) -> bool:
    compact_line = _compact_korean_keyword_text(line)
    for keyword in PRIMARY_AMOUNT_KEYWORDS:
        if _compact_korean_keyword_text(keyword) in compact_line:
            return True
    return False


def _compact_korean_keyword_text(value: str) -> str:
    return re.sub(r"[\s:：·ㆍ\-\|_/\\\[\]().]+", "", str(value or "")).lower()


def _format_amount_text(amount: Optional[int]) -> Optional[str]:
    if amount is None:
        return None
    return "₩{0:,}".format(amount)


def _raw_excerpt(text: str) -> str:
    excerpt = re.sub(r"\s+", " ", text).strip()
    return excerpt[:500]


def _log_runtime_warning_once(runtime_name: str, message: str, exc: Exception) -> None:
    if runtime_name in _WARNED_RUNTIMES:
        return
    _WARNED_RUNTIMES.add(runtime_name)
    logger.warning("%s Detail: %s", message, exc)
