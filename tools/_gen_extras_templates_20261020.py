"""Một lần (20/10/2026): sinh mẫu CHÈN MỚI lower-third + callout-left/right cho 4 shop (covers:false), dùng _base.css
của từng shop (font + màu đúng nhận diện). Sửa style ở bảng STYLE rồi chạy lại để sinh đồng loạt."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.templates import SHOPS  # noqa: E402

STYLE = {  # nền thanh/hộp, chữ, dòng phụ, viền/nhấn, màu chấm
    "giadungplus_official": {"bg": "#c01818", "fg": "#ffffff", "sub": "#ffe3e3", "accent": "#ffffff", "dot": "#c01818",
                             "title_font": "", "sub_font": ""},
    "phaledo_official": {"bg": "linear-gradient(180deg,#1f1f1f,#121212)", "fg": "#ffffff", "sub": "#e8e2d8",
                         "accent": "#b89a6a", "dot": "#161616", "title_font": "", "sub_font": ""},
    "lteng_vn": {"bg": "linear-gradient(40deg,#0b649c,#062955 55%,#041e40)", "fg": "#ffffff", "sub": "#d6e8f7",
                 "accent": "#19b6c8", "dot": "#0b649c", "title_font": "", "sub_font": ""},
    "lteng_hcm": {"bg": "linear-gradient(180deg,#8f1f1a,#5a1410)", "fg": "#ffffff", "sub": "#f3d9d6",
                  "accent": "#111111", "dot": "#a83030", "title_font": "", "sub_font": "font-family:\"Avo\",sans-serif;"},
}

LOWER = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><link rel="stylesheet" href="_base.css">
<style>
  /* LOWER THIRD — CHÈN MỚI (covers:false): thanh tên ở mép dưới-trái, không dùng để che chữ Trung */
  #label {{ background: none; border: 0; justify-content: flex-start; padding: 0; }}
  #bar {{ display: flex; align-items: stretch; height: 100%; max-width: 100%; box-sizing: border-box; }}
  #accent {{ flex: none; width: max(4px, calc(var(--h) * 0.08)); background: {accent}; }}
  #box {{ display: flex; flex-direction: column; justify-content: center; gap: calc(var(--h) * 0.03);
          padding: calc(var(--h) * 0.1) calc(var(--h) * 0.4) calc(var(--h) * 0.1) calc(var(--h) * 0.25);
          background: {bg}; border-radius: 0 calc(var(--h) * 0.1) calc(var(--h) * 0.1) 0; min-width: 0; flex: 1; }}
  #text {{ color: {fg}; text-align: left; {title_font} }}
  #sub {{ color: {sub}; text-align: left; {sub_font} }}
</style></head>
<body><div id="label"><div id="bar"><div id="accent"></div><div id="box"><div id="text">{{{{text}}}}</div><div id="sub">{{{{sub}}}}</div></div></div></div></body></html>
"""

CALLOUT = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><link rel="stylesheet" href="_base.css">
<style>
  /* CALLOUT — CHÈN MỚI (covers:false): hộp chữ + đường chỉ + chấm tròn; renderer đặt TÂM CHẤM đúng điểm mục tiêu */
  #label {{ background: none; border: 0; padding: 0; flex-direction: {direction}; justify-content: flex-start; }}
  #box {{ flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center;
          padding: 0 calc(var(--h) * 0.35); height: 72%; background: {bg}; border-radius: calc(var(--h) * 0.12);
          box-shadow: 0 calc(var(--h) * 0.04) calc(var(--h) * 0.12) rgba(0,0,0,.35); }}
  #text {{ color: {fg}; {title_font} }}
  #line {{ flex: none; width: calc(var(--h) * 0.9); height: max(2px, calc(var(--h) * 0.045)); background: #ffffff;
           box-shadow: 0 0 calc(var(--h) * 0.05) rgba(0,0,0,.5); }}
  #dot {{ flex: none; width: calc(var(--h) * 0.34); height: calc(var(--h) * 0.34); border-radius: 50%; box-sizing: border-box;
          background: {dot}; border: max(2px, calc(var(--h) * 0.06)) solid #ffffff; box-shadow: 0 0 calc(var(--h) * 0.08) rgba(0,0,0,.45); }}
</style></head>
<body><div id="label"><div id="box"><div id="text">{{{{text}}}}</div></div><div id="line"></div><div id="dot"></div></div></body></html>
"""

for shop, st in STYLE.items():
    d = SHOPS / shop / "templates"
    (d / "lower-third.html").write_text(LOWER.format(**st), encoding="utf-8", newline="\n")
    (d / "callout-left.html").write_text(CALLOUT.format(direction="row", **st), encoding="utf-8", newline="\n")
    (d / "callout-right.html").write_text(CALLOUT.format(direction="row-reverse", **st), encoding="utf-8", newline="\n")
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    m["slots"]["lower-third"] = {"file": "lower-third.html", "use": "CHÈN MỚI: thanh tên dưới-trái (tiêu đề + dòng phụ)",
                                 "fs_min": 30, "fs_max": 50, "covers": False}
    for side in ("left", "right"):
        m["slots"][f"callout-{side}"] = {"file": f"callout-{side}.html",
                                         "use": f"CHÈN MỚI: chỉ vào chi tiết sản phẩm, hộp chữ bên {'trái' if side == 'left' else 'phải'} điểm chỉ",
                                         "fs_min": 30, "fs_max": 50, "covers": False, "nowrap": True}
    (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ok", shop)
