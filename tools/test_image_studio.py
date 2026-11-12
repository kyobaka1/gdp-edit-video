"""Test Image Studio (image-studio/) — không cần app, không cần API: dựng ảnh giả rồi kiểm bộ dựng + bộ QA.

  .venv\\Scripts\\python.exe tools\\test_image_studio.py

Kiểm: (1) layout đúng → ĐẠT, ảnh ra giữ kích thước nền, tông chữ tự chọn theo nền; (2) từng lỗi cố ý đều bị QA bắt
(chữ đè sản phẩm, chữ Hán, tràn ảnh, chữ quá nhỏ, khối đè nhau, chữ chìm vào nền, xuống quá số dòng)."""

import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "image-studio"))
for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

from imslib import JOBS, kit  # noqa: E402
from imslib.render import Studio  # noqa: E402

SHOP = "phaledo_official"
job = JOBS / "_test"
shutil.rmtree(job, ignore_errors=True)
(job / "clean").mkdir(parents=True)
W, H = 1000, 1000
dark = Image.new("RGB", (W, H), (38, 30, 26))
dark.paste(Image.new("RGB", (400, 450), (170, 110, 70)), (300, 450))     # "sản phẩm" giả
dark.save(job / "clean" / "dark.png")
Image.new("RGB", (W, 1333), (244, 236, 222)).save(job / "clean" / "light.png")

KEEP = [[30, 45, 70, 90]]
GOOD = {"kind": "cover", "base": "clean/dark.png", "keep": KEEP, "blocks": [
    {"id": "h", "type": "headline", "text": "BẢO HÀNH BỂ VỠ", "x": 50, "y": 20, "w": 90, "size": 64, "lines": 1},
    {"id": "p", "type": "pills", "items": ["1 ĐỔI 1", "180 NGÀY"], "x": 50, "y": 32, "size": 44}]}


def bad(**change):
    spec = {**GOOD, "blocks": [dict(b) for b in GOOD["blocks"]]}
    for k, v in change.items():
        if k == "add":
            spec["blocks"].append(v)
        else:
            spec["blocks"][0][k] = v
    return spec


CASES = {  # tên → (layout, chuỗi phải có trong thông báo LỖI; None = phải ĐẠT)
    "dung": (GOOD, None),
    "nen-sang": ({"kind": "description_image", "base": "clean/light.png", "blocks": [
        {"id": "h", "type": "headline", "text": "MỘT THÌA LÀ VỪA", "x": 50, "y": 15, "w": 88, "size": 60, "lines": 1},
        {"id": "s", "type": "sub", "text": "Hũ đường thuỷ tinh nắp gỗ keo", "x": 50, "y": 22, "size": 28}]}, None),
    "de-san-pham": (bad(y=60), "đè lên vùng sản phẩm"),
    "chu-han": (bad(text="一勺刚好"), "chữ Hán"),
    "tran-anh": (bad(x=97, anchor="center-left", w=None), "tràn ra ngoài"),
    "qua-nho": (bad(add={"id": "n", "type": "text", "text": "chữ li ti", "x": 50, "y": 40, "size": 11}), "quá nhỏ"),
    "de-nhau": (bad(add={"id": "d", "type": "sub", "text": "Dòng phụ nằm trùng nhãn", "x": 50, "y": 32, "size": 30}), "đè lên khối"),
    "chim-nen": (bad(color="dark"), "khó đọc"),
    "bia-chu-day": (bad(y=93), "vùng khung Shopee"),
    "qua-dong": (bad(text="BẢO HÀNH BỂ VỠ MỘT ĐỔI MỘT TRONG VÒNG MỘT TRĂM TÁM MƯƠI NGÀY KỂ TỪ NGÀY NHẬN HÀNG", lines=1, w=60, nowrap=False), None),
}

theme = kit.load(SHOP)
fails = []
with Studio() as st:
    for name, (spec, want) in CASES.items():
        r = st.render(job, name, spec, theme)
        errs = [i["msg"] for i in r["issues"] if i["level"] == "LỖI"]
        warns = [i["msg"] for i in r["issues"] if i["level"] == "CẢNH BÁO"]
        out = Image.open(job / r["out"])
        base = Image.open(job / spec["base"])
        ok = out.size == base.size
        if name == "qua-dong":                               # chữ dài 1 dòng → tự co, phải có cảnh báo co chữ
            ok = ok and any("bị co" in m for m in warns)
        elif want is None:
            ok = ok and not errs
        else:
            ok = ok and any(want in m for m in errs)
        if name == "dung":
            ok = ok and r["tones"].get("h") == "light"
        if name == "nen-sang":
            ok = ok and r["tones"].get("h") == "dark" and r["logo"]["file"].endswith("-ink")
        print(f"{'✓' if ok else '✗'} {name:<12} lỗi={errs} cảnh báo={warns}")
        if not ok:
            fails.append(name)
shutil.rmtree(job, ignore_errors=True)
print("\nĐẠT" if not fails else f"\nHỎNG: {fails}")
sys.exit(1 if fails else 0)
