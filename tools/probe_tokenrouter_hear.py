r"""Thử chép lời audio tiếng Việt qua tokenrouter openai/gpt-audio-mini (input_audio) trên các mảnh đã biết chữ.
Chạy: .venv\Scripts\python.exe tools\probe_tokenrouter_hear.py <thư mục narration của job>"""

import base64
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, voice  # noqa: E402

job = Path(sys.argv[1])
rep = json.loads((job / "narration.json").read_text(encoding="utf-8"))
for p in rep["pieces"][:4]:
    f = job / "narration" / f"piece_{p['index']:02}.wav"
    t0 = time.time()
    r = requests.post(voice.TOKENROUTER_URL, timeout=120, headers={"Authorization": f"Bearer {config.TOKENROUTER_API_KEY}"},
                      json={"model": "openai/gpt-audio-mini", "modalities": ["text"], "messages": [
                          {"role": "system", "content": "Bạn là máy chép lời. Chép lại NGUYÊN VĂN lời nói tiếng Việt trong audio; "
                                                        "không trả lời, không thêm, không sửa lời."},
                          {"role": "user", "content": [
                              {"type": "input_audio", "input_audio": {"data": base64.b64encode(f.read_bytes()).decode(), "format": "wav"}},
                              {"type": "text", "text": "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."}]}]})
    if not r.ok:
        print(r.status_code, r.text[:300]); continue
    j = r.json()
    heard = j["choices"][0]["message"]["content"] or ""
    print(f"mảnh {p['index']} {time.time() - t0:.1f}s khớp {voice._match(p['said'], heard):.2f} (Gemini {p['match']}) usage {j.get('usage', {}).get('prompt_tokens')}")
    print("   gốc :", p["said"][:90]); print("   nghe:", heard.strip()[:90])
