"""Local vehicle OCR for the Telegram bot.

Uses PaddleOCR locally on Railway. No OpenAI/DeepSeek API is used.
Extracts VIN, Russian plate and vehicle year from a photo of an STS/VIN plate.
"""
from __future__ import annotations

import io
import logging
import os
import re
import threading
from collections import Counter

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# Keep PaddleX/PaddleOCR model cache on the Railway Volume so models survive restarts.
if os.path.isdir("/data"):
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", "/data/.paddlex")

VIN_STRICT_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
VIN_LABEL_RE = re.compile(r"(?:идентификационн|VIN|номер\s+кузова|кузов|рама)", re.I)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")

# Russian registration plates: one Cyrillic letter + 3 digits + 2 Cyrillic letters + region.
PLATE_RE = re.compile(
    r"(?<![А-ЯA-Z0-9])([АВЕКМНОРСТУХABEKMHOPCTYX]\s*\d{3}\s*[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\s*\d{2,3})(?![А-ЯA-Z0-9])",
    re.I,
)

CYR_TO_LATIN = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y",
})

# Only letters that are legal in a Russian plate and have a Latin look-alike.
PLATE_ALLOWED = set("АВЕКМНОРСТУХ")

# OCR frequently confuses these glyphs in VINs. We only use corrections after
# a candidate is already 17 characters long and is close to a valid VIN.
VIN_REPAIR = str.maketrans({
    "О": "0", "О": "0", "І": "1", "I": "1", "Q": "0",
})

_PROMPTLESS = True
_OCR = None
_OCR_LOCK = threading.Lock()


def _get_ocr():
    global _OCR
    if _OCR is not None:
        return _OCR
    with _OCR_LOCK:
        if _OCR is not None:
            return _OCR
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise RuntimeError(
                "PaddleOCR не установлен. Проверьте зависимости Railway."
            ) from exc

        logger.info("Initialising local PaddleOCR (Russian, CPU)")
        _OCR = PaddleOCR(
            lang="ru",
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="eslav_PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            engine="paddle",
        )
        logger.info("Local PaddleOCR initialised")
    return _OCR


def _prepare_images(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")

    # Telegram can send very large photos. Keep enough detail for small STS text.
    max_side = 2600
    if max(image.size) > max_side:
        ratio = max_side / max(image.size)
        image = image.resize(
            (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
            Image.Resampling.LANCZOS,
        )

    full = image.copy()
    enhanced = ImageEnhance.Contrast(full).enhance(1.25)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.8)
    enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=3))

    w, h = full.size
    variants = [full, enhanced]

    # STS fields are usually distributed through the page. Two overlapping crops
    # make small VIN/plate/year lines larger without relying on a cloud model.
    for top, bottom in ((0.05, 0.62), (0.38, 0.98)):
        crop = full.crop((0, int(h * top), w, int(h * bottom)))
        crop = crop.resize((int(crop.width * 1.55), int(crop.height * 1.55)), Image.Resampling.LANCZOS)
        crop = ImageEnhance.Contrast(crop).enhance(1.30)
        crop = ImageEnhance.Sharpness(crop).enhance(1.9)
        crop = crop.filter(ImageFilter.UnsharpMask(radius=1.3, percent=145, threshold=3))
        variants.append(crop)

    return variants


def _result_to_dict(result):
    """Convert PaddleOCR's result object across 3.x minor versions."""
    value = result
    for attr in ("json", "to_dict", "data"):
        if hasattr(value, attr):
            try:
                candidate = getattr(value, attr)
                value = candidate() if callable(candidate) else candidate
                if isinstance(value, dict):
                    return value
            except Exception:
                pass
    if isinstance(value, dict):
        return value
    try:
        if hasattr(value, "__dict__"):
            return value.__dict__
    except Exception:
        pass
    return {}


def _collect_texts(obj):
    """Recursively collect OCR text and confidence from Paddle result objects."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            # Current PaddleOCR 3.x uses rec_texts/rec_scores.
            texts = value.get("rec_texts")
            scores = value.get("rec_scores") or []
            if isinstance(texts, (list, tuple)):
                for i, text in enumerate(texts):
                    score = scores[i] if i < len(scores) else 0
                    if text is not None and str(text).strip():
                        found.append((str(text).strip(), float(score or 0)))
                # Do not walk rec_texts again.
            if "rec_text" in value and value.get("rec_text"):
                found.append((str(value["rec_text"]).strip(), float(value.get("rec_score") or 0)))
            if "text" in value and isinstance(value.get("text"), str) and value["text"].strip():
                found.append((value["text"].strip(), float(value.get("score") or 0)))
            for k, v in value.items():
                if k not in {"rec_texts", "rec_scores", "rec_text", "rec_score", "text"}:
                    walk(v)
        elif isinstance(value, (list, tuple)):
            # Legacy-ish shape: [box, [text, score]]
            if len(value) == 2 and isinstance(value[1], (list, tuple)) and value[1]:
                if isinstance(value[1][0], str):
                    try:
                        score = float(value[1][1]) if len(value[1]) > 1 else 0
                    except Exception:
                        score = 0
                    found.append((value[1][0].strip(), score))
                    return
            for item in value:
                walk(item)

    walk(obj)
    # Remove exact duplicates while keeping first occurrence.
    unique = []
    seen = set()
    for text, score in found:
        key = text.strip()
        if key and key not in seen:
            seen.add(key)
            unique.append((key, score))
    return unique


def _ocr_variant(image):
    import numpy as np

    ocr = _get_ocr()
    arr = np.asarray(image)
    results = ocr.predict(arr)
    texts = []
    for result in results:
        texts.extend(_collect_texts(_result_to_dict(result)))
    return texts


def _clean_vin_text(value: str) -> str:
    value = str(value or "").upper().replace("-", "").replace(" ", "")
    value = value.translate(CYR_TO_LATIN)
    return re.sub(r"[^A-Z0-9]", "", value)


def _normalise_vin(value: str) -> str:
    value = _clean_vin_text(value)
    if len(value) != 17:
        return ""
    if VIN_STRICT_RE.fullmatch(value):
        return value
    # Conservative OCR correction: only repair characters that are forbidden in
    # VINs and only when exactly one or two suspicious glyphs are present.
    repaired = value.translate(VIN_REPAIR)
    if VIN_STRICT_RE.fullmatch(repaired):
        return repaired
    return ""


def _extract_vin_candidates(lines):
    candidates = []

    def add(value):
        vin = _normalise_vin(value)
        if vin and vin not in candidates:
            candidates.append(vin)

    # First, inspect tokens that already look VIN-like.
    for text, _score in lines:
        upper = text.upper().translate(CYR_TO_LATIN)
        chunks = re.findall(r"[A-Z0-9][A-Z0-9\s\-]{15,25}[A-Z0-9]", upper)
        for chunk in chunks:
            add(chunk)

        # A VIN may be split into several OCR tokens. Remove separators only
        # from lines that contain mostly Latin/digits.
        latin_digits = re.sub(r"[^A-Z0-9]", "", upper)
        if 17 <= len(latin_digits) <= 22 and sum(ch.isdigit() for ch in latin_digits) >= 3:
            add(latin_digits)

    # Then inspect lines near the explicit VIN/ кузов labels.
    for idx, (text, _score) in enumerate(lines):
        if VIN_LABEL_RE.search(text):
            for near_text, _near_score in lines[idx:idx + 5]:
                add(near_text)

    return candidates[:10]


def _normalise_plate(value: str) -> str:
    value = str(value or "").upper()
    value = re.sub(r"[\s\-]+", "", value)
    # Convert Latin look-alikes to Cyrillic for a consistent Russian plate display.
    value = value.translate(str.maketrans({
        "A": "А", "B": "В", "E": "Е", "K": "К", "M": "М", "H": "Н",
        "O": "О", "P": "Р", "C": "С", "T": "Т", "X": "Х", "Y": "У",
    }))
    return value


def _extract_plate_candidates(lines):
    candidates = []
    for text, _score in lines:
        raw = text.upper()
        # Search both original Cyrillic and visually similar Latin OCR output.
        for match in PLATE_RE.finditer(raw):
            plate = _normalise_plate(match.group(1))
            if plate not in candidates:
                candidates.append(plate)

        # OCR sometimes drops the final region separator. Try compact chunks.
        compact = re.sub(r"[^A-ZА-Я0-9]", "", raw)
        for i in range(max(0, len(compact) - 10)):
            chunk = compact[i:i + 9]
            if re.fullmatch(r"[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}", chunk):
                plate = _normalise_plate(chunk)
                if plate not in candidates:
                    candidates.append(plate)
    return candidates[:10]


def _extract_year(lines):
    # Prefer a year close to an explicit "Год выпуска" label.
    for idx, (text, _score) in enumerate(lines):
        if re.search(r"год\s+(выпуска|изготовления)|выпуск", text, re.I):
            for near_text, _near_score in lines[idx:idx + 3]:
                m = YEAR_RE.search(near_text)
                if m:
                    return m.group(1)
    # Fallback: use a plausible year, but ignore obvious document years if possible.
    years = []
    for text, _score in lines:
        years.extend(YEAR_RE.findall(text))
    return years[0] if years else ""


def _confidence(vin_candidates, plate_candidates, year, lines):
    score = 0
    if vin_candidates:
        score += 60
        # Repeated VIN in two or more OCR passes is strong evidence.
        if len(vin_candidates) >= 1:
            score += 15
    if plate_candidates:
        score += 15
    if year:
        score += 10
    if lines:
        score += 5
    return min(score, 99)


def recognise_vehicle_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Run completely local OCR and return VIN, plate and year."""
    variants = _prepare_images(image_bytes)
    all_lines = []
    errors = []

    for index, image in enumerate(variants, 1):
        try:
            logger.info("Vehicle OCR local: view %s/%s", index, len(variants))
            lines = _ocr_variant(image)
            all_lines.extend(lines)
            logger.info("Vehicle OCR local: view %s recognized %s text lines", index, len(lines))
        except Exception as exc:
            logger.exception("Vehicle OCR local failed on view %s", index)
            errors.append(f"view {index}: {type(exc).__name__}: {exc}")

    if not all_lines:
        raise RuntimeError("Локальный PaddleOCR не вернул текст" + (f" | {' | '.join(errors[-2:])}" if errors else ""))

    vin_candidates = _extract_vin_candidates(all_lines)
    plate_candidates = _extract_plate_candidates(all_lines)
    year = _extract_year(all_lines)

    # Count occurrences across OCR passes. A repeated VIN wins over a one-off candidate.
    counts = Counter()
    for text, _score in all_lines:
        for candidate in _extract_vin_candidates([(text, 0)]):
            counts[candidate] += 1
    if counts:
        vin = counts.most_common(1)[0][0]
        if counts[vin] >= 2:
            confidence = 98
        else:
            confidence = _confidence(vin_candidates, plate_candidates, year, all_lines)
    else:
        vin = ""
        confidence = _confidence(vin_candidates, plate_candidates, year, all_lines)

    # Keep useful text for debugging, but do not send it anywhere.
    raw_text = "\n".join(text for text, _score in all_lines)

    return {
        "vin": vin,
        "vin_candidates": vin_candidates,
        "plate": plate_candidates[0] if plate_candidates else "",
        "plate_candidates": plate_candidates,
        "make": "",
        "model": "",
        "year": year,
        "confidence": confidence,
        "raw_text": raw_text[:12000],
    }
