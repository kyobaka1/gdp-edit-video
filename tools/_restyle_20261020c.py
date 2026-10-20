"""Một lần (20/10/2026, Sếp góp ý mẫu): (1) đệm trái/phải rộng hơn, (2) thêm đệm trên/dưới,
(3) GDP + LTENG HCM viền mỏng hơn, bo góc nhỏ hơn. Sửa theo chuỗi chính xác — báo lỗi nếu không khớp."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.templates import SHOPS  # noqa: E402

PAD = {  # slot → (trên/dưới, trái/phải) theo bội số --h
    "caption": (0.16, 0.6), "hook": (0.12, 0.55), "badge": (0.14, 0.5), "info": (0.14, 0.45),
}
pad_re = re.compile(r"padding: 0 calc\(var\(--h\) \* [0-9.]+\)")
for shop in ("giadungplus_official", "phaledo_official", "lteng_vn", "lteng_hcm"):
    for slot, (v, h) in PAD.items():
        f = SHOPS / shop / "templates" / f"{slot}.html"
        s = f.read_text(encoding="utf-8")
        new, n = pad_re.subn(f"padding: calc(var(--h) * {v}) calc(var(--h) * {h})", s)
        if n != 1:
            raise SystemExit(f"{shop}/{slot}: tìm thấy {n} chỗ padding (cần đúng 1)")
        f.write_text(new, encoding="utf-8", newline="\n")

EXACT = {  # (file, cũ, mới)
    "giadungplus_official": [
        ("caption.html", "border-radius: calc(var(--h) * 0.15)", "border-radius: calc(var(--h) * 0.1)"),
        ("hook.html", "border: max(3px, calc(var(--h) * 0.05)) solid #ffffff;", "border: max(2px, calc(var(--h) * 0.028)) solid #ffffff;"),
        ("hook.html", "border-radius: calc(var(--h) * 0.15);", "border-radius: calc(var(--h) * 0.1);"),
        ("hook.html", "box-shadow: 0 0 0 max(1px, calc(var(--h) * 0.02)) #7a1010;", "box-shadow: 0 0 0 1px #7a1010;"),
        ("badge.html", "border: max(3px, calc(var(--h) * 0.06)) solid #c01818; border-radius: calc(var(--h) * 0.15);",
         "border: max(2px, calc(var(--h) * 0.032)) solid #c01818; border-radius: calc(var(--h) * 0.1);"),
        ("info.html", "border-radius: calc(var(--h) * 0.15);", "border-radius: calc(var(--h) * 0.1);"),
        ("info.html", "border-bottom: max(3px, calc(var(--h) * 0.06)) solid #7a1010;", "border-bottom: max(2px, calc(var(--h) * 0.035)) solid #7a1010;"),
    ],
    "lteng_hcm": [
        ("_base.css", "border-radius: calc(var(--h) * 0.15);", "border-radius: calc(var(--h) * 0.1);"),
        ("caption.html", "border-left: max(4px, calc(var(--h) * 0.08)) solid #111111;", "border-left: max(3px, calc(var(--h) * 0.05)) solid #111111;"),
        ("hook.html", "border: max(3px, calc(var(--h) * 0.05)) solid #111111;", "border: max(2px, calc(var(--h) * 0.028)) solid #111111;"),
        ("badge.html", "border: max(3px, calc(var(--h) * 0.05)) solid #a83030;", "border: max(2px, calc(var(--h) * 0.03)) solid #a83030;"),
        ("info.html", "border-top: max(3px, calc(var(--h) * 0.06)) solid #111111;", "border-top: max(2px, calc(var(--h) * 0.035)) solid #111111;"),
    ],
}
for shop, edits in EXACT.items():
    for name, old, new in edits:
        f = SHOPS / shop / "templates" / name
        s = f.read_text(encoding="utf-8")
        if s.count(old) != 1:
            raise SystemExit(f"{shop}/{name}: '{old[:50]}…' xuất hiện {s.count(old)} lần (cần 1)")
        f.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("ok")
