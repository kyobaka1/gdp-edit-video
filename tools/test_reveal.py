"""Kiểm thử chữ hiện dần + khối nhấn (Sếp 29/10, học từ skill brag) — vì sao từng điều quan trọng:

  1  CHE PHỦ: ô ở MỌI bước hiện dần (kể cả 0 chữ) phải đục y như ô đủ chữ → chữ Trung không lộ lúc chữ Việt chưa ra.
     (so kênh alpha của từng ảnh bước với ảnh đủ chữ, mẫu có nền của cả 4 shop)
  2  KHÔNG ĐỔI JOB CŨ: chữ không có `*` và không bật hiện dần → HTML/ảnh y hệt renderer trước (fx=False).
  3  ĐỌC TRƯỚC: ô không đủ thời gian đọc (0,25s/âm tiết, ≥0,8s) sau khi hiện xong → bỏ hiện dần, vẫn giữ nhịp bật
     khối nhấn; ô đủ dài → hiện dần xong trong ≤0,7s.
  4  KHỐI NHẤN là một bước riêng (không bị gộp với chữ thường) + dấu câu dính liền sau khối không bị tách.

Chạy: .\\.venv\\Scripts\\python.exe tools\\test_reveal.py   (cần Chrome như test_font_gate; không gọi API)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import ImageChops  # noqa: E402

from studio import motion  # noqa: E402
from studio.templates import TemplateRenderer, _units_html  # noqa: E402

ok = bad = 0


def check(cond: bool, msg: str) -> None:
    global ok, bad
    ok, bad = ok + bool(cond), bad + (not cond)
    print(f"  [{'ĐẠT' if cond else 'LỖI'}] {msg}")


print("== 1 che phủ (alpha mọi bước = alpha ô đủ chữ)")
for shop in ("giadungplus_official", "lteng_vn", "lteng_hcm", "phaledo_official"):
    with TemplateRenderer(shop) as r:
        for slot in ("caption", "hook", "info"):
            full, w, h = r.render(slot, "Kệ treo *không cần khoan* chịu lực", 640, 90, sub="Dòng phụ" if slot == "info" else "",
                                  min_px=29, max_w=720, fx=True)
            st = r.states(motion.reveal_steps(r.units()))
            opaque = lambda im: im.getchannel("A").point(lambda v: 255 if v > 250 else 0)  # noqa: E731
            same = all(ImageChops.difference(opaque(s), opaque(full)).getbbox() is None for s in st["shots"])
            sizes = all(s.size == full.size for s in st["shots"] + list(st["punch"].values()))
            check(same and sizes, f"{shop}/{slot}: {len(st['shots'])} bước, ô trống đục như ô đủ chữ, cùng cỡ {full.size}")

print("== 2 job cũ không đổi")
with TemplateRenderer("giadungplus_official") as r:
    a, _, _ = r.render("caption", "Kệ treo tường không cần khoan", 640, 90, min_px=29, max_w=720)
    html_old = r._page.evaluate("() => document.getElementById('text').innerHTML")
    b, _, _ = r.render("caption", "Kệ treo tường không cần khoan", 640, 90, min_px=29, max_w=720, fx=False)
    check("<span" not in html_old, "không `*`, fx=False → HTML chữ trơn (không bọc khối)")
    check(ImageChops.difference(a, b).getbbox() is None, "hai lần render fx=False ra cùng ảnh")

print("== 3 đọc trước, hiệu ứng sau")
shots = [f"s{j}" for j in range(5)]
base = {"s0": 4.75, "start": 5.0, "end": 5.0, "anim_in": "slide-up", "e1": 0.0,
        "fx": {"shots": shots, "punch": {2: "p2"}, "punch_full": "pf", "reveal": True}}
short = {**base, "end": 6.4, "e1": 6.58, "floor": motion.read_floor("Nắp gỗ óc chó đậy kín")}  # 1,4s, cần 1,5s
motion.schedule(short)
check(not short["revealed"] and short["punch_at"] and any(p == "pf" for p, _ in short["seq"]),
      "ô 1,4s / 6 âm tiết: bỏ hiện dần, vẫn bật khối nhấn (ảnh đủ chữ + nhấn)")
check(short["seq"][0][0] == "s0", "ô vào với nền TRỐNG trước (không mờ chéo 2 câu đầy chữ)")
long_ = {**base, "end": 8.0, "e1": 8.18, "floor": motion.read_floor("Nắp gỗ óc chó đậy kín")}
motion.schedule(long_)
check(long_["revealed"] and long_["full_at"] - 4.9 <= motion.REVEAL_MAX + motion.PUNCH + 0.01,
      f"ô 3s: hiện dần, đủ chữ lúc {long_['full_at']}s (≤0,7s + nhịp bật)")
check(abs(sum(d for _, d in long_["seq"]) - (long_["e1"] - long_["s0"])) < 0.01, "lịch ảnh phủ kín s0..e1 (không hở khung)")

print("== 4 khối nhấn")
check(motion.reveal_steps([False] * 3 + [True] + [False] * 8) == [2, 3, 4, 6, 8, 10, 12],
      "câu 12 khối: 2 khối/bước nhưng khối nhấn (thứ 4) đứng riêng một bước")
check('bừa bộn</span><span class="u">,</span>' in _units_html("Bồn rửa *bừa bộn*, đồ không chỗ để"),
      "dấu phẩy dính liền sau khối nhấn (không chèn khoảng trắng → không ra 'BỪA BỘN ,')")

print(f"\nTỔNG: {ok}/{ok + bad} đạt")
sys.exit(1 if bad else 0)
