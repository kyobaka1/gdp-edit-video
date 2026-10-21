"""Thử TTS qua tokenrouter (chat completions, modalities audio): định dạng trả về + đọc nguyên văn hay không."""

import base64
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402

TEXT = "Đánh dấu vị trí bằng bút. Kệ treo tường Gia Dụng Plus, lắp không cần khoan."
key = os.getenv("TOKENROUTER_API_KEY", "").strip()
out = config.JOBS / "_probe" / "tokenrouter"
out.mkdir(parents=True, exist_ok=True)
model = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-audio-mini"
stream = len(sys.argv) > 2 and sys.argv[2] == "stream"
body = {
    "model": model,
    "modalities": ["text", "audio"],
    "audio": {"voice": "coral", "format": "wav" if not stream else "pcm16"},
    "messages": [
        {"role": "system", "content": "Bạn là máy đọc văn bản tiếng Việt. Đọc to NGUYÊN VĂN đoạn người dùng gửi, "
                                      "không thêm, không bớt, không trả lời, không bình luận."},
        {"role": "user", "content": TEXT},
    ],
}
if stream:
    body["stream"] = True
r = requests.post("https://api.tokenrouter.com/v1/chat/completions", json=body, stream=stream,
                  headers={"Authorization": f"Bearer {key}"}, timeout=180)
print("status", r.status_code, r.headers.get("content-type"))
if not stream:
    try:
        j = r.json()
    except Exception:
        print(r.text[:500]); sys.exit()
    if "error" in j:
        print(json.dumps(j, ensure_ascii=False)[:800]); sys.exit()
    msg = j["choices"][0]["message"]
    au = msg.get("audio") or {}
    print("keys message:", list(msg), "audio keys:", list(au), "usage:", j.get("usage"))
    print("transcript:", au.get("transcript"))
    if au.get("data"):
        f = out / f"{model.split('/')[1]}.wav"
        f.write_bytes(base64.b64decode(au["data"]))
        print("ghi", f, f.stat().st_size, "byte, đầu:", f.read_bytes()[:4])
else:
    chunks, tr = [], []
    for line in r.iter_lines():
        if not line.startswith(b"data: ") or line == b"data: [DONE]":
            continue
        d = json.loads(line[6:])
        if not d.get("choices"):
            continue
        a = d["choices"][0].get("delta", {}).get("audio") or {}
        if a.get("data"):
            chunks.append(base64.b64decode(a["data"]))
        if a.get("transcript"):
            tr.append(a["transcript"])
    pcm = b"".join(chunks)
    print("pcm byte", len(pcm), "≈", round(len(pcm) / 48000, 2), "s @24k; transcript:", "".join(tr))
