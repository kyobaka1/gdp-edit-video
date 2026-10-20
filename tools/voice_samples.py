"""Mẫu nghe thử giọng đọc từng shop (shop.json voice): đọc 1 câu có tên brand, kiểm ngược, ghi WAV → jobs/_voices/.
Chạy: .venv\\Scripts\\python.exe tools\\voice_samples.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402
from studio.narration import _tts  # noqa: E402
from studio.templates import shop_voice  # noqa: E402
from studio.voice import _match, spoken  # noqa: E402

LINES = {
    "giadungplus_official": "Đồ dùng phòng tắm bừa bộn? Có ngay kệ treo tường Gia Dụng Plus, lắp không cần khoan.",
    "lteng_vn": "Kệ treo tường LTENG, chịu lực tốt, lắp nhanh trong vài phút, không cần khoan tường.",
    "lteng_hcm": "Kệ LTENG chắc chắn, bền bỉ, dán là chắc, phòng tắm gọn gàng ngay hôm nay.",
    "phaledo_official": "Phòng tắm gọn gàng và tinh tế hơn với kệ treo tường PHALEDO, nhỏ gọn mà sang trọng.",
}
out = config.JOBS / "_voices"
out.mkdir(parents=True, exist_ok=True)
for shop, text in LINES.items():
    v = shop_voice(shop)
    said = spoken(text)
    f = out / f"{shop}_{v['name']}.wav"
    heard = _tts(said, v["name"], f)
    print(f"{shop:22} {v['name']:8} {v['gender']:3} khớp {_match(said, heard):.2f} → {f.name} | nghe: {heard.strip()[:70]}")
