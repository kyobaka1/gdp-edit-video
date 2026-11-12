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
    # Sếp 12/11: chỉ GÓC DƯỚI-TRÁI bị khung che — dải đáy bên phải đặt chữ được
    "bia-chu-day-phai": (bad(add={"id": "r", "type": "badge", "text": "DÁN TƯỜNG", "x": 96.5, "y": 96, "anchor": "bottom-right", "size": 40}), None),
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
# ---------- ẢNH PHÂN LOẠI: khung phân biệt dùng chung cho cả bộ (imslib/variant.py) ----------
from imslib import variant  # noqa: E402

wide = Image.new("RGB", (1000, 1000), (186, 178, 168))                    # sản phẩm NGANG nằm nửa trên
wide.paste(Image.new("RGB", (600, 350), (90, 84, 80)), (200, 200))
wide.save(job / "clean" / "wide.png")
tall = Image.new("RGB", (750, 1000), (186, 178, 168))                     # sản phẩm DỌC, ảnh nguồn 3:4
tall.paste(Image.new("RGB", (300, 600), (90, 84, 80)), (225, 200))
tall.save(job / "clean" / "tall.png")
SET = {"style": "bottom", "chips": ["NHÔM KHÔNG GỈ", "BẢN DÀY 1.2MM"], "included": {"items": ["keo-dan", "oc-vit"]},
       "warranty": {"value": "10", "unit": "NĂM"}}
LAYOUT = {"variant_set": SET, "images": {
    "a": {"kind": "variant_image", "base": "clean/wide.png", "keep": [[20, 20, 80, 55]], "variant": {"name": "30CM", "sub": "BASIC"}},
    "b": {"kind": "variant_image", "base": "clean/wide.png", "keep": [[20, 20, 80, 55]],
          "variant": {"name": "50CM", "sub": "THANH TREO\n+ MÓC"}}}}
vtheme = kit.load("lteng_vn")


def vrender(st, key, spec, vset):
    r = st.render(job, key, spec, vtheme, {**vset, "_all": variant.collect(LAYOUT)})
    return r, [i["msg"] for i in r["issues"] if i["level"] == "LỖI"], Image.open(job / r["out"]).size


def vcheck(name, ok, note=""):
    print(f"{'✓' if ok else '✗'} {name:<22} {note}")
    if not ok:
        fails.append(name)


with Studio() as st:
    reps = {}
    for key in ("a", "b"):                                   # khung bên dưới: ĐẠT, ảnh ra vuông, sản phẩm không bị che
        reps[key], errs, size = vrender(st, key, LAYOUT["images"][key], SET)
        vcheck(f"pl-duoi-{key}", not errs and size == (1000, 1000) and reps[key]["card"]["style"] == "bottom", f"lỗi={errs}")
    pt = {k: {b["id"]: b.get("size_pt") for b in r["blocks"]} for k, r in reps.items()}
    vcheck("pl-cung-co-chu", pt["a"]["ten"] == pt["b"]["ten"] and pt["a"]["kieu"] == pt["b"]["kieu"] and not variant.consistency(LAYOUT, reps),
           f"tên {pt['a']['ten']} / {pt['b']['ten']} · kiểu {pt['a']['kieu']} / {pt['b']['kieu']}")
    r, errs, size = vrender(st, "c", {"kind": "variant_image", "base": "clean/tall.png", "keep": [[30, 20, 70, 80]],
                                      "variant": {"name": "XÁM", "sub": "3 TẦNG"}}, {**SET, "style": "right"})
    vcheck("pl-ben-phai", not errs and size == (1000, 1000), f"lỗi={errs}")                     # nguồn 3:4 → ra vuông
    r, errs, size = vrender(st, "d", {"kind": "variant_image", "base": "clean/dark.png", "keep": KEEP,
                                      "variant": {"name": "30CM"}}, SET)
    vcheck("pl-tu-can-san-pham", not errs and r["blocks"] and size == (1000, 1000), f"lỗi={errs}")   # sản phẩm nằm thấp → ảnh tự dịch lên
    r, errs, size = vrender(st, "d2", {"kind": "variant_image", "base": "clean/dark.png", "keep": [[30, 3, 70, 98]],
                                       "variant": {"name": "30CM"}}, SET)
    vcheck("pl-khung-che-sp", any("che sản phẩm" in m for m in errs), f"lỗi={errs}")            # sản phẩm cao kín ảnh → khung che
    try:
        vrender(st, "d3", LAYOUT["images"]["a"], {**SET, "panel": 31})
        vcheck("pl-khung-qua-to", False, "khung bên dưới > 20% phải bị từ chối")
    except SystemExit as exc:
        vcheck("pl-khung-qua-to", "lấn sản phẩm" in str(exc))
    r, errs, size = vrender(st, "e", {"kind": "variant_image", "base": "clean/wide.png", "keep": [[20, 20, 80, 55]],
                                      "variant": {"name": "KỆ GÓC TAM GIÁC BA TẦNG SÁU MÓC", "sub": "LOẠI DÀY ĐẶC BIỆT CÓ THANH TREO KHĂN"}},
                            {**SET, "panel": 16})
    small = [b.get("size_pt") for b in r["blocks"] if b["id"] == "ten"][0]
    vcheck("pl-ten-qua-dai", small < 60 and any("nhỏ" in i["msg"] or "tràn ô" in i["msg"] for i in r["issues"]), f"tên co còn {small}pt")
    fill = {"style": "fill", "blocks": [{"id": "ten", "type": "badge", "text": "{name}", "x": 50, "y": 80, "size": 44},
                                        {"id": "kieu", "type": "text", "text": "{sub}", "x": 50, "y": 90, "size": 30, "bold": True}]}
    r, errs, size = vrender(st, "f", {"kind": "variant_image", "base": "clean/wide.png", "keep": [[20, 20, 80, 55]],
                                      "variant": {"name": "50CM", "sub": "Thanh treo + móc"}}, fill)
    vcheck("pl-dien-khung-co-san", not errs and size == (1000, 1000) and {"ten", "kieu"} <= {b["id"] for b in r["blocks"]}, f"lỗi={errs}")
    try:
        vrender(st, "g", LAYOUT["images"]["a"], {})
        vcheck("pl-chua-chon-style", False, "phải dừng khi chưa chọn variant_set.style")
    except SystemExit as exc:
        vcheck("pl-chua-chon-style", "variant_set.style" in str(exc))

shutil.rmtree(job, ignore_errors=True)
print("\nĐẠT" if not fails else f"\nHỎNG: {fails}")
sys.exit(1 if fails else 0)
