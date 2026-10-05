"""Vehicle/VIN OCR tuned for Russian vehicle registration certificates (STS) and VIN photos."""
import base64
import io
import json
import logging
import os
import re
import urllib.error
import urllib.request

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")
logger = logging.getLogger(__name__)

SCHEMA = {
    "type": "object",
    "properties": {
        "vin": {"type": "string"},
        "vin_candidates": {"type": "array", "items": {"type": "string"}},
        "plate": {"type": "string"},
        "plate_candidates": {"type": "array", "items": {"type": "string"}},
        "make": {"type": "string"},
        "model": {"type": "string"},
        "year": {"type": "string"},
        "confidence": {"type": "number"},
        "raw_text": {"type": "string"},
    },
    "required": [
        "vin", "vin_candidates", "plate", "plate_candidates",
        "make", "model", "year", "confidence", "raw_text"
    ],
    "additionalProperties": False,
}

VIN_RE = re.compile(r"(?<![A-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Z0-9])")
VIN_LABEL_RE = re.compile(r"(?:Идентификационный\s+номер|VIN|номер\s+кузова|кузов|рама)", re.I)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def _clean_alnum(value):
    if not value:
        return ""
    value = str(value).upper()
    # OCR often returns Cyrillic lookalikes from Russian documents.
    value = value.translate(str.maketrans({
        "О": "O", "А": "A", "В": "B", "С": "C", "Е": "E",
        "К": "K", "М": "M", "Н": "H", "Р": "P", "Т": "T",
        "Х": "X", "У": "Y",
    }))
    return re.sub(r"[^A-Z0-9]", "", value)


def _normalise_vin(value):
    value = _clean_alnum(value)
    if len(value) == 17 and not any(ch in value for ch in "IOQ"):
        return value
    return ""


def _candidate_from_near_vin_line(line: str):
    """Extract 17-char VIN from a line even when OCR inserted spaces/hyphens."""
    cleaned = _clean_alnum(line)
    # Prefer a 17-char suffix because STS lines often contain a label followed by VIN.
    if len(cleaned) >= 17:
        for i in range(0, len(cleaned) - 16):
            part = cleaned[i:i + 17]
            if _normalise_vin(part):
                return part
    return ""


def _vin_candidates(data):
    candidates = []

    def add(value):
        cleaned = _clean_alnum(value)
        if len(cleaned) == 17 and cleaned not in candidates:
            candidates.append(cleaned)

    for value in [data.get("vin"), *(data.get("vin_candidates") or [])]:
        add(value)

    raw = str(data.get("raw_text") or "")
    # First search exact 17-char runs.
    for match in VIN_RE.findall(_clean_alnum(raw)):
        add(match)

    # Then inspect individual OCR lines around VIN/кузов labels. This catches
    # values such as "X U F 1 5 6 ..." or values separated by punctuation.
    lines = raw.splitlines()
    for idx, line in enumerate(lines):
        if VIN_LABEL_RE.search(line):
            for nearby in lines[idx:idx + 3]:
                add(_candidate_from_near_vin_line(nearby))

    # Finally inspect every short-ish line. STS VIN is often printed on its own line.
    for line in lines:
        if 15 <= len(_clean_alnum(line)) <= 22:
            add(_candidate_from_near_vin_line(line))

    return candidates


def _normalise_plate(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().upper())


def _normalise_year(value):
    if not value:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", str(value))
    return m.group(1) if m else ""


def _jpeg_data_url(img, quality=90):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _prepare_images(image_bytes: bytes, mime_type: str):
    """Create full-frame and overlapping detail crops so small STS VIN text is readable."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")

        # Do not downscale the user's original too aggressively: VIN characters on
        # STS can be only a few pixels high. Cap at 2200px on the long side.
        max_side = 2200
        if max(image.size) > max_side:
            ratio = max_side / max(image.size)
            image = image.resize(
                (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
                Image.Resampling.LANCZOS,
            )

        # Full image.
        full = image.copy()

        # A clean enhanced full image.
        enhanced = ImageEnhance.Contrast(full).enhance(1.20)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.6)
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.3, percent=120, threshold=3))

        w, h = full.size
        # STS layouts commonly place VIN in the upper/middle portion, but we do
        # overlapping bands rather than hard-coding one exact position.
        bands = [
            (0.05, 0.48),
            (0.27, 0.70),
            (0.49, 0.92),
        ]
        crops = []
        for top, bottom in bands:
            crop = full.crop((0, int(h * top), w, int(h * bottom)))
            # Double the crop so the model receives much larger VIN characters.
            scale = 1.7 if crop.width < 2000 else 1.35
            crop = crop.resize(
                (int(crop.width * scale), int(crop.height * scale)),
                Image.Resampling.LANCZOS,
            )
            crop = ImageEnhance.Contrast(crop).enhance(1.25)
            crop = ImageEnhance.Sharpness(crop).enhance(1.8)
            crop = crop.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))
            crops.append(crop)

        # Limit to 5 images: full + enhanced + 3 focused bands.
        return [_jpeg_data_url(full), _jpeg_data_url(enhanced)] + [_jpeg_data_url(c) for c in crops]
    except Exception:
        return [f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"]


PROMPT = """
Ты — специалист по OCR автомобильных документов РФ. Перед тобой фотографии одного и того же
документа/автомобиля. На изображениях могут быть СТС, VIN-табличка или VIN под стеклом.

ТВОЯ ГЛАВНАЯ ЗАДАЧА — ТОЧНО НАЙТИ VIN.

Для российского СТС особенно внимательно ищи:
1) строку «Идентификационный номер (VIN)»;
2) строку «Кузов (кабина, прицеп) №» — там VIN/номер кузова часто повторяется;
3) строку с маркой;
4) строку с моделью;
5) строку «Год выпуска ТС»;
6) строку с государственным регистрационным номером.

VIN обычно содержит РОВНО 17 латинских букв и цифр. В VIN не используются I, O и Q.
Не путай VIN с серией/номером СТС, номером паспорта ТС, номером документа, номером двигателя
или регистрационным номером.

КРИТИЧЕСКИ ВАЖНО:
- Сначала мысленно прочитай текст на всех изображениях.
- Сравни полный кадр и увеличенные фрагменты.
- Если VIN повторяется в двух местах документа, сравни оба значения. Совпадающее значение
  является самым надёжным кандидатом.
- Даже если dedicated поле vin заполнить трудно, ОБЯЗАТЕЛЬНО добавь все правдоподобные
  17-символьные варианты в vin_candidates.
- Если OCR разделил VIN пробелами, собери символы обратно.
- Не заменяй символы наугад. Если есть сомнение, добавь вариант в vin_candidates и снизь confidence.
- raw_text должен содержать полезный распознанный текст, особенно строки вокруг VIN.
- Для госномера используй только то, что реально видно на фото.
- Если поле не читается, оставь его пустым.
""".strip()


def _call(image_data_urls, api_key, model, structured=True):
    content = [{"type": "input_text", "text": PROMPT}]
    for url in image_data_urls:
        content.append({"type": "input_image", "image_url": url, "detail": "high"})

    payload = {
        "model": model,
        "input": [{"role": "user", "content": content}],
        "store": False,
    }
    if structured:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": "vehicle_data",
                "strict": True,
                "schema": SCHEMA,
            }
        }
    else:
        payload["text"] = {"format": {"type": "json_object"}}

    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    text = result.get("output_text", "")
    data = _extract_json(text)
    if not data:
        # Defensive fallback for responses where SDK/server does not populate output_text.
        for item in result.get("output", []) or []:
            for part in item.get("content", []) or []:
                if part.get("type") == "output_text":
                    data = _extract_json(part.get("text", ""))
                    if data:
                        break
            if data:
                break
    return data


def recognise_vehicle_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в Railway Variables")

    image_urls = _prepare_images(image_bytes, mime_type)
    logger.info("Vehicle OCR: prepared %d image views", len(image_urls))

    errors = []
    models = [DEFAULT_MODEL]
    for fallback in ("gpt-4.1-mini", "gpt-4o-mini"):
        if fallback not in models:
            models.append(fallback)

    data = {}
    for model in models:
        try:
            logger.info("Vehicle OCR: calling model %s", model)
            data = _call(image_urls, api_key, model, structured=True)
            if data:
                logger.info("Vehicle OCR: structured response received from %s", model)
                break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            errors.append(f"{model}: HTTP {exc.code}: {detail}")
            logger.exception("Vehicle OCR HTTP error from %s", model)
        except Exception as exc:
            errors.append(f"{model}: {type(exc).__name__}: {exc}")
            logger.exception("Vehicle OCR error from %s", model)

    if not data:
        try:
            logger.info("Vehicle OCR: trying JSON-mode fallback")
            data = _call(image_urls, api_key, DEFAULT_MODEL, structured=False)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            errors.append(f"fallback: HTTP {exc.code}: {detail}")
            logger.exception("Vehicle OCR fallback HTTP error")
        except Exception as exc:
            errors.append(f"fallback: {type(exc).__name__}: {exc}")
            logger.exception("Vehicle OCR fallback error")

    if not data:
        raise RuntimeError("; ".join(errors) or "Пустой ответ OCR API")

    candidates = _vin_candidates(data)
    vin = next((_normalise_vin(v) for v in candidates if _normalise_vin(v)), "")

    # If the model returned the same VIN twice, increase confidence: this is
    # particularly useful for STS where VIN is repeated in the кузов field.
    normalized = [_normalise_vin(v) for v in candidates]
    duplicates = [v for v in set(normalized) if v]
    confidence = max(0, min(100, float(data.get("confidence") or 0)))
    if vin and sum(1 for v in normalized if v == vin) >= 2:
        confidence = max(confidence, 98.0)

    return {
        "vin": vin,
        "vin_candidates": candidates[:5],
        "plate": _normalise_plate(
            data.get("plate") or
            ((data.get("plate_candidates") or [""])[0] if data.get("plate_candidates") else "")
        ),
        "make": str(data.get("make") or "").strip(),
        "model": str(data.get("model") or "").strip(),
        "year": _normalise_year(data.get("year")),
        "confidence": confidence,
        "raw_text": str(data.get("raw_text") or "").strip(),
    }
