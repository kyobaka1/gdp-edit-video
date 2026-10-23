"""Nhập 10 animation Claude Design đầu tiên (Sếp 23/10) vào thư viện assets/motion/ + điền metadata.

  .venv\\Scripts\\python.exe tools\\_seed_motion_20261023.py <thư mục nguồn đã gom>

Nguồn: project Claude Design 554580b5… (GDP Motion 01/02/03/08, LTENG Motion 01–04, PHALEDO Motion 01–02 + ảnh
assets/). Chạy 1 lần; lần sau thêm animation mới dùng `vs.py motion import` (không cần script, không sửa code)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import motionlib as ml  # noqa: E402

ORIGIN = "Claude Design project 554580b5-089f-4f21-941f-26ffd3c26f26"
TOP_BOTTOM = [{"y": 0.18}, {"y": 0.8}]  # brand reveal: dải trên (chỗ logo cũ) hoặc dải dưới — tránh vùng sản phẩm giữa

SEED = [
    # file, id, brand, roles, metadata thêm
    ("gdp-motion-01.html", "gdp-roll-smile", "GIADUNGPLUS", ["brand_reveal"], {
        "priority": 60, "tags": ["thân thiện", "vui", "logo cười", "lăn"],
        "params": {"x": 540, "y": 960, "size": 560},
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Logo lăn vào từ mép trái, cười, chữ trượt vào, lăn ra mép phải (4s). Lăn ngang cả khung → giữ "
                 "scale 1 (khung thiết kế phủ đúng bề ngang video); cỡ logo chỉnh bằng params.size."}),
    ("gdp-motion-08.html", "gdp-orbit-settle", "GIADUNGPLUS", ["brand_reveal"], {
        "priority": 50, "tags": ["thân thiện", "vui", "logo cười"],
        "params": {"format": "9x16", "anchor": "center", "scale": 0.9},
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Icon bay vòng quỹ đạo vào từ mép trái, dừng, cười, chữ trượt vào, thu & mờ (3.5s)."}),
    ("gdp-motion-03.html", "gdp-peek-a-boo", "GIADUNGPLUS", ["accent"], {
        "priority": 40, "tags": ["vui", "ló ra", "nhỏ"], "replaces": [],
        "params": {"side": "left", "verticalPosition": 0.3, "size": 0.18},
        "placement": {"x": "design", "y": "design", "scale": 1.0, "candidates": [
            {"params": {"side": "left"}, "y": 0.3}, {"params": {"side": "right"}, "y": 0.3},
            {"params": {"side": "left"}, "y": 0.55}]},
        "notes": "Icon ló ra từ mép trái/phải, cười, rút về (2.5s). x=design giữ đúng mép."}),
    ("gdp-motion-02.html", "gdp-ghost-smile", "GIADUNGPLUS", ["watermark"], {
        "priority": 50, "tags": ["watermark", "logo cười"], "replaces": ["watermark"], "ends_transparent": False,
        "hold": "last", "params": {"anchor": "upper-right", "width": 0.16, "hold": 0.14, "dur": 3.8},
        "variants": {"on_light": {"variant": "red"}, "on_dark": {"variant": "white"}}, "default_variant": "on_light",
        "placement": {"width_pct": 0.13},
        "notes": "Logo hiện, nghiêng cười rồi mờ xuống ~14% và GIỮ (watermark sống). Khung cuối = watermark giữ."}),
    ("lteng-motion-01.html", "lteng-precision-assembly", "LTENG", ["brand_reveal"], {
        "priority": 55, "tags": ["chính xác", "kỹ thuật", "lắp ráp", "guide lines"],
        "params": {"width": 0.6, "nx": 0.5, "ny": 0.5, "subline": 1},
        "variants": {"on_dark": {}}, "default_variant": "on_dark",
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Guide lines → dựng từng nét L T E N G → khớp → magenta + BLUE VINE (4s). Artwork TRẮNG → chỉ dùng "
                 "trên footage tối (biến thể on_dark)."}),
    ("lteng-motion-02.html", "lteng-rail-glide", "LTENG", ["brand_reveal"], {
        "priority": 50, "tags": ["chính xác", "tuyến tính", "công nghệ"],
        "params": {"format": "9x16", "anchor": "center", "scale": 1, "direction": "ltr"},
        "variants": {"on_dark": {"color": "white"}, "on_light": {"color": "navy"}}, "default_variant": "on_dark",
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Logo trượt theo ray vào từ trái rồi ra trái (3s)."}),
    ("lteng-motion-03.html", "lteng-magenta-signal", "LTENG", ["brand_reveal"], {
        "priority": 45, "tags": ["công nghệ", "ngắn", "magenta"],
        "params": {"anchor": "center", "scale": 0.8},
        "variants": {"on_dark": {"colorVariant": "white"}, "on_light": {"colorVariant": "navy"}}, "default_variant": "on_dark",
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Vạch magenta mở ra chữ LTENG (2s) — sting ngắn."}),
    ("lteng-motion-04.html", "lteng-ghost-signature", "LTENG", ["watermark"], {
        "priority": 50, "tags": ["watermark", "kỹ thuật"], "replaces": ["watermark"], "ends_transparent": False,
        "hold": "last", "params": {"mode": "intro", "anchor": "upper-left", "width": 0.3, "hold": 0.14},
        "variants": {"on_dark": {"variant": "white"}, "on_light": {"variant": "navy"}}, "default_variant": "on_dark",
        "placement": {"width_pct": 0.3},
        "notes": "Chữ LTENG hiện rồi lắng ở ~14% và GIỮ (watermark). Khung cuối = watermark giữ."}),
    ("phaledo-motion-01.html", "phaledo-crystal-aperture", "PHALEDO", ["brand_reveal"], {
        "priority": 55, "tags": ["cao cấp", "tối giản", "ánh sáng", "thuỷ tinh"],
        "params": {"width": 0.5, "nx": 0.5, "ny": 0.5},
        "variants": {"on_dark": {"tone": "light"}, "on_light": {"tone": "dark"}}, "default_variant": "on_dark",
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Vòng sáng champagne khép lại, chữ PHALEDO mở từ giữa, ® hiện (4.2s). Ánh sáng là gradient cùng màu "
                 "mờ dần về alpha 0 — overlay thường, không khúc xạ footage."}),
    ("phaledo-motion-02.html", "phaledo-refraction-sweep", "PHALEDO", ["brand_reveal"], {
        "priority": 50, "tags": ["cao cấp", "tối giản", "ánh sáng", "thuỷ tinh"],
        "params": {"anchor": "center", "scale": 0.9, "lightDirection": "ltr"},
        "variants": {"on_dark": {"colorVariant": "dark"}, "on_light": {"colorVariant": "light"}}, "default_variant": "on_dark",
        "placement": {"x": "design", "scale": 1.0, "candidates": TOP_BOTTOM},
        "notes": "Dải sáng quét qua, chữ chuyển kính → đặc, ® hiện, ánh sáng rời (3.2s). Quang học chỉ mô phỏng TRONG chữ + "
                 "dải sáng (RGBA), footage bên dưới không bị bẻ cong. Logo đặc ở ~1.9–2.5s → dùng làm watermark "
                 "(shop.json watermark.hold_at 2.45)."}),
]


def main(src: Path) -> None:
    for fname, aid, brand, roles, extra in SEED:
        res = ml.import_source(src / fname, anim_id=aid, brands=[brand], roles=roles, test_render=False)
        p = res["anim"]["dir"] / "motion.json"
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta.update(extra)
        meta["source"]["origin"] = f"{ORIGIN} / {fname}"
        p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        a = ml.get(aid)
        for v in (list(a["variants"]) or [None]):
            info = ml.render(a, v)
            c = info["check"]
            print(f"{aid:26} {v or '-':9} bbox {info['bbox']} {info['frames']} khung {info['render_seconds']}s "
                  f"α đầu {c['first_alpha_max']} cuối {c['last_alpha_max']} halo {c['halo']} "
                  f"{'⚠ ' + '; '.join(c['warn']) if c['warn'] else 'OK'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
