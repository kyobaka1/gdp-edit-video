"""Gọi Gemini trả JSON có schema. Ghi log token để đo chi phí thật mỗi video."""

import json
import time
from pathlib import Path

from google import genai
from google.genai import types

from studio import config

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("Thiếu GEMINI_API_KEY trong .env")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def image_part(path: Path) -> types.Part:
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg")


def generate_json(contents: list, schema: dict, *, usage_log: Path | None = None, label: str = "",
                  max_output_tokens: int = 16384, retries: int = 3) -> dict | list:
    """generate_content với response_json_schema; thử lại khi lỗi mạng hoặc JSON hỏng."""
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0,
        max_output_tokens=max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = client().models.generate_content(model=config.GEMINI_MODEL, contents=contents, config=cfg)
            text = resp.text or ""
            data = json.loads(text)
            if usage_log is not None and resp.usage_metadata:
                u = resp.usage_metadata
                with usage_log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "label": label, "model": config.GEMINI_MODEL,
                        "prompt": u.prompt_token_count, "output": u.candidates_token_count,
                        "thoughts": u.thoughts_token_count, "total": u.total_token_count,
                    }) + "\n")
            return data
        except json.JSONDecodeError as exc:
            last_exc = RuntimeError(f"JSON hỏng (đuôi: {text[-200:]!r})")
        except Exception as exc:  # mạng / quota / 5xx
            last_exc = exc
        time.sleep(2 * attempt)
    raise RuntimeError(f"Gemini thất bại sau {retries} lần [{label}]: {last_exc}")
