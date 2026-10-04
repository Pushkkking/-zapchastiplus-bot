"""OCR helpers for VIN / license-plate photos.

Uses OpenAI Responses API with an image-capable model. The API key is read from
OPENAI_API_KEY; no key is stored in the repository.
"""
import base64
import json
import os
import re
import urllib.error
import urllib.request


OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")


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
    value = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    # VINs do not contain I, O or Q. OCR frequently confuses these with 1/0.
    value = value.replace("О", "O").replace("О", "O")
    return value


def _normalise_plate(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().upper())


def recognise_vehicle_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Return {vin, plate, make, model, confidence, raw_text} from a photo."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в Railway Variables")

    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    prompt = """
Ты распознаёшь данные автомобиля на фотографии для автосервиса.
Нужно внимательно прочитать именно визуально видимые данные и вернуть ТОЛЬКО JSON.

Поля JSON:
{
  "vin": "VIN или пустая строка",
  "plate": "госномер или пустая строка",
  "make": "марка, если явно видна, иначе пустая строка",
  "model": "модель, если явно видна, иначе пустая строка",
  "confidence": 0-100,
  "raw_text": "другой полезный текст с фото"
}

Правила:
- VIN обычно 17 символов; не придумывай отсутствующие символы.
- Госномер возвращай в читаемом виде, без выдумывания региона.
- Если символ сомнителен, лучше оставить поле пустым, чем угадывать.
- Не путай номер детали, серийный номер или артикул с VIN.
- Не считай штрихкод VIN, если сам VIN текстом не виден.
""".strip()

    payload = {
        "model": DEFAULT_MODEL,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url, "detail": "high"},
            ],
        }],
    }
    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Ошибка OCR API ({exc.code}): {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Не удалось выполнить OCR: {exc}") from exc

    result = json.loads(body)
    text = result.get("output_text", "")
    data = _extract_json(text)
    return {
        "vin": _normalise_vin(data.get("vin")),
        "plate": _normalise_plate(data.get("plate")),
        "make": str(data.get("make") or "").strip(),
        "model": str(data.get("model") or "").strip(),
        "confidence": data.get("confidence", 0),
        "raw_text": str(data.get("raw_text") or "").strip(),
    }
