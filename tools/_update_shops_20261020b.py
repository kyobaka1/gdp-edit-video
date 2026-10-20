"""Một lần (20/10/2026): ghi font + logo (tên file Sếp đặt) + brand kit prod (gradient/badge/typography) vào shop.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.templates import SHOPS  # noqa: E402

UPDATES = {
    "giadungplus_official": {
        "templates_from": None,
        "fonts": {"heading": "UTM Avo/UTM_AvoBold.ttf", "body": "UTM Avo/UTM_Avo.ttf",
                  "rule": "UTM Avo mọi trường hợp (Bold + Regular)"},
        "style": "tone đỏ/trắng: chữ trắng nền đỏ · chữ đen viền trắng · chữ đỏ viền trắng",
        "logo_files": {"primary": "logo/logo-red-white.png", "on_dark": "logo/logo-white-red.png",
                       "on_light": "logo/nguyen-ban-tach-nen.png"},
        "brand_kit": {"badge": {"bg": "#f1c40f", "text": "#c01818"},
                      "typography": {"header": "Bold, ALL CAPS, 1 hàng, 6-8 từ", "sub": "Regular, tối đa 2 dòng, factual"},
                      "text_radius_pct": 15},
        "notes": "",
    },
    "phaledo_official": {
        "templates_from": None,
        "fonts": {"heading": "Averta/Averta-Bold.otf", "body": "Averta/Averta-Regular.otf",
                  "rule": "Averta mọi trường hợp (áp cho cả shop phaledo)"},
        "style": "tone tối, chữ trắng có bóng nhẹ",
        "logo_files": {"primary": "logo/logo-ngang.png", "on_dark": "logo/logo-tach-nen.png"},
        "brand_kit": {"cover_style": "minimal_premium", "heading_color": "#f2e9e3",
                      "badge": {"bg": "#c0b7a6", "text": "#f2e9e3", "bg_opacity": 35, "border": "#f2e9e3"},
                      "typography": {"header": "Bold, ALL CAPS, ≤5 từ/hàng, tối đa 2 hàng", "sub": "Regular, 1 dòng ngắn, factual"},
                      "text_radius_pct": 15},
        "notes": "",
    },
    "phaledo": {
        "templates_from": "phaledo_official",
        "fonts": {"heading": "Averta/Averta-Bold.otf", "body": "Averta/Averta-Regular.otf", "rule": "Averta (theo phaledo_official)"},
        "style": "theo phaledo_official: tone tối, chữ trắng có bóng nhẹ",
        "logo_files": {"primary": "logo/logo-ngang.png", "on_dark": "logo/logo-tach-nen.png"},
        "notes": "Sếp 20/10: dùng chung nhận diện phaledo_official (mẫu chữ mượn qua templates_from). Bảng màu prod của shop này còn mặc định.",
    },
    "lteng_vn": {
        "templates_from": None,
        "fonts": {"heading": "UTM Avo/UTM_AvoBold.ttf", "body": "UTM Avo/UTM_Avo.ttf", "rule": "UTM Avo"},
        "style": "xanh dương gradient",
        "logo_files": {"primary": "logo/logo-ngang.png", "icon": "logo/logo-nen-trang-vuong.jpg"},
        "brand_kit": {"cover_style": "badge_heavy",
                      "heading_gradient": {"angle": 40, "stops": ["#0b649c", "#062955", "#041e40"]},
                      "badge": {"bg": "#004878", "text": "#ffffff", "gradient": {"angle": 15, "stops": ["#0b649c", "#062955", "#041E40"]}},
                      "typography": {"header": "Bold, ALL CAPS, ≤5 từ/hàng, tối đa 2 hàng, chữ rất lớn", "sub": "Regular, 1 dòng ngắn, factual"},
                      "text_radius_pct": 15},
        "notes": "",
    },
    "lteng_hcm": {
        "templates_from": None,
        "fonts": {"heading": "UTM HelvetIns/UTM HelvetIns.ttf", "body": "UTM Avo/UTM_Avo.ttf", "body_bold": "UTM Avo/UTM_AvoBold.ttf",
                  "rule": "UTM HelvetIns cho tiêu đề/nhấn mạnh, UTM Avo cho chữ thường"},
        "style": "đen / đỏ sậm: nền đỏ sậm chữ trắng · chữ đen bọc trắng · chữ đỏ sậm viền trắng",
        "logo_files": {"primary": "logo/logo-ngang.png", "icon": "logo/logo-vuong.jpg"},
        "brand_kit": {"cover_style": "badge_heavy",
                      "heading_gradient": {"angle": 90, "stops": ["#c0392b", "#a83030", "#5a1410"]},
                      "badge": {"bg": "#c0392b", "text": "#ffffff"},
                      "typography": {"header": "Bold, ALL CAPS, ≤5 từ/hàng, tối đa 2 hàng, chữ rất lớn",
                                     "badge": "Chip góc trên nền đỏ chữ trắng bold", "sub": "Regular, 1 dòng ngắn, factual"},
                      "text_radius_pct": 15},
        "notes": "",
    },
}

for code, up in UPDATES.items():
    p = SHOPS / code / "shop.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    logo_files = up.pop("logo_files")
    doc["logo"]["files"] = logo_files  # đúng tên file Sếp thả; thiếu dạng nào thì không khai
    doc.update(up)
    missing = [f for f in logo_files.values() if not (SHOPS / code / f).exists()]
    if missing:
        raise SystemExit(f"{code}: logo khai nhưng không thấy file {missing}")
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ok", code)
