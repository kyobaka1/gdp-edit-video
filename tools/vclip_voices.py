r"""Liệt kê giọng của tài khoản tts.vclip.io (trang "Giọng nói của bạn") + giọng shop nào đang dùng.
Chạy: .venv\Scripts\python.exe tools\vclip_voices.py   → chép `id` vào assets/shops/<shop>/shop.json voice.vclip"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402
from studio.voice import vclip_voices  # noqa: E402

used: dict[str, list[str]] = {}
for p in sorted((config.ROOT / "assets" / "shops").glob("*/shop.json")):
    v = json.loads(p.read_text(encoding="utf-8")).get("voice") or {}
    if v.get("vclip"):
        used.setdefault(v["vclip"], []).append(p.parent.name)
for v in vclip_voices():
    shops = ", ".join(used.get(v["id"], [])) or "-"
    print(f"{v['id']}  {v['name']:28}  shop: {shops}\n    {v['description'][:150]}")
