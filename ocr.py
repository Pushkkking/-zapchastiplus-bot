"""Vehicle document/photo recognition via OpenAI Responses API."""
import base64
import json
import os
import re
import urllib.error
import urllib.request

OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

SCHEMA = {
    "type": "object",
    "properties": {
        "vin": {"type": "string"},
        "plate": {"type": "string"},
        "make": {"type": "string"},
        "model": {"type": "string"},
        "year": {"type": "string"},
        "confidence": {"type": "number"},
        "raw_text": {"type": "string"},
    },
    "required": ["vin", "plate", "make", "model", "year", "confidence", "raw_text"],
    "additionalProperties": False,
}


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


def _normalise_vin(value):
    if not value:
        return ""
    value = str(value).upper().replace("О", "O")
    value = re.sub(r"[^A-Z0-9]", "", value)
    # Never silently invent a VIN. A valid VIN has 17 characters and no I/O/Q.
    if len(value) == 17 and not any(ch in value for ch in "IOQ"):
        return value
    return value if 3 <= len(value) <= 30 else ""


def _normalise_plate(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().upper())


def _normalise_year(value):
    if not value:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", str(value))
    return m.group(1) if m else ""


def _call(image_data_url, api_key, model, structured=True):
    prompt = """
Ты распознаёшь данные автомобиля на фотографии СТС, другого автомобильного документа,
VIN-таблички или фотографии VIN под лобовым стеклом.

Верни данные только по тому, что реально видно на фотографии. Ничего не придумывай.
Если поле не видно или есть сомнение — верни пустую строку.

Нужно определить:
- vin — VIN автомобиля, обычно 17 символов;
- plate — государственный регистрационный номер;
- make — марка автомобиля;
- model — модель автомобиля;
- year — год выпуска автомобиля;
- confidence — общая уверенность от 0 до 100;
- raw_text — другой полезный текст, который удалось прочитать.

Если это СТС, особенно внимательно ищи марку, модель, год, VIN и госномер в соответствующих полях документа.
Не путай VIN с номером документа, серийным номером, номером кузова другого объекта или артикулом.
""".strip()

    payload = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image_data_url, "detail": "high"},
            ],
        }],
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
    with urllib.request.urlopen(req, timeout=75) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body)
    return _extract_json(result.get("output_text", ""))


def recognise_vehicle_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в Railway Variables")

    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    errors = []
    models = [DEFAULT_MODEL]
    if DEFAULT_MODEL != "gpt-4o-mini":
        models.append("gpt-4o-mini")

    data = {}
    for model in models:
        try:
            data = _call(data_url, api_key, model, structured=True)
            if data:
                break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            errors.append(f"{model}: HTTP {exc.code}: {detail}")
        except Exception as exc:
            errors.append(f"{model}: {exc}")

    # Last fallback for an account/model combination where Structured Outputs is unavailable.
    if not data:
        try:
            data = _call(data_url, api_key, DEFAULT_MODEL, structured=False)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            errors.append(f"fallback: HTTP {exc.code}: {detail}")
        except Exception as exc:
            errors.append(f"fallback: {exc}")

    if not data:
        raise RuntimeError("; ".join(errors) or "Пустой ответ OCR API")

    return {
        "vin": _normalise_vin(data.get("vin")),
        "plate": _normalise_plate(data.get("plate")),
        "make": str(data.get("make") or "").strip(),
        "model": str(data.get("model") or "").strip(),
        "year": _normalise_year(data.get("year")),
        "confidence": max(0, min(100, float(data.get("confidence") or 0))),
        "raw_text": str(data.get("raw_text") or "").strip(),
    }
