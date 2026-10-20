"""Kiểm cổng font của renderer: mẫu trỏ font không tồn tại PHẢI bị chặn (Chrome mặc định lặng lẽ thay font khác).
Chạy: .venv\\Scripts\\python.exe tools\\test_font_gate.py  → in "CHẶN ĐÚNG" và thoát 0."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.templates import SHOPS, TemplateRenderer  # noqa: E402

root = SHOPS / "_test_badfont"
tpl = root / "templates"
tpl.mkdir(parents=True, exist_ok=True)
try:
    (root / "shop.json").write_text(json.dumps({"shop": "_test_badfont", "templates_from": None}), encoding="utf-8")
    (tpl / "manifest.json").write_text(json.dumps(
        {"slots": {"caption": {"file": "c.html", "use": "t", "fs_min": 30, "fs_max": 60}}}), encoding="utf-8")
    (tpl / "c.html").write_text(
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        '@font-face{font-family:"X";src:url("../../../fonts/KHONG_CO.ttf")}'
        '#label{width:var(--w);height:var(--h);background:#000}#text{font-family:"X";font-size:var(--fs);color:#fff}'
        '</style></head><body><div id="label"><div id="text">{{text}}</div></div></body></html>', encoding="utf-8")
    with TemplateRenderer("_test_badfont") as r:
        try:
            r.render("caption", "Thử", 300, 80)
        except FileNotFoundError as exc:
            print("CHẶN ĐÚNG:", exc)
            sys.exit(0)
    print("KHÔNG CHẶN — cổng font hỏng")
    sys.exit(1)
finally:
    shutil.rmtree(root, ignore_errors=True)
