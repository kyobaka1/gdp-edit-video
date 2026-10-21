"""Dò nhà cung cấp TTS dự phòng: model Gemini TTS có sẵn + danh mục model audio của tokenrouter (không in key)."""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, gemini  # noqa: E402

print("== Gemini models có 'tts' ==")
for m in gemini.client().models.list():
    if "tts" in m.name:
        print(" ", m.name, getattr(m, "display_name", ""))

key = os.getenv("TOKENROUTER_API_KEY", "").strip()
print("\n== tokenrouter: key", "CÓ" if key else "THIẾU", "==")
r = requests.get("https://api.tokenrouter.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
print("GET /v1/models", r.status_code)
try:
    data = r.json().get("data", [])
    ids = [d.get("id") for d in data]
    print("tổng", len(ids))
    for d in data:
        if "audio" in (d.get("id") or "") or "tts" in (d.get("id") or ""):
            print(" ", {k: d.get(k) for k in ("id", "architecture", "pricing") if k in d})
except Exception as exc:
    print("không đọc được JSON:", r.text[:300], exc)
