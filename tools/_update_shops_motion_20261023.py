"""Một lần (23/10/2026): cấu hình animation thương hiệu RIÊNG từng shop (shop.json.motion + watermark động).

Thư viện animation dùng chung theo brand (assets/motion/); shop chỉ khai CÁCH DÙNG: luật AUTO, tag ưu tiên, override,
animation watermark thay chữ. Hai shop cùng brand (LTENG VN / HCM) dùng chung file, khác cấu hình."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.templates import SHOPS  # noqa: E402

REVEAL_ONLY = {"brand_reveal": {"max": 1, "window": [1.0, 0.6]}}
MOTION = {
    "giadungplus_official": {
        "auto": REVEAL_ONLY,
        "prefer_tags": ["thân thiện", "vui", "logo cười"],
        "exclude": [], "overrides": {},
        "note": "Tính cách GDP: thân thiện, gần gũi, vui — logo cười, chuyển động mềm. Peek-a-Boo (accent) chèn tay.",
    },
    "lteng_vn": {
        "auto": REVEAL_ONLY,
        "prefer_tags": ["chính xác", "kỹ thuật", "lắp ráp"],
        "exclude": [], "overrides": {},
        "note": "LTENG VN: chính xác, kỹ thuật — ưu tiên Precision Assembly / Rail Glide.",
    },
    "lteng_hcm": {
        "auto": REVEAL_ONLY,
        "prefer_tags": ["công nghệ", "ngắn", "magenta"],
        "exclude": [],
        "overrides": {"lteng-rail-glide": {"params": {"direction": "rtl"}}},
        "note": "LTENG HCM dùng chung thư viện LTENG nhưng khác cách dùng: ưu tiên sting ngắn Magenta Signal, "
                "Rail Glide chạy chiều ngược (rtl), watermark nhỏ hơn VN.",
    },
    "phaledo_official": {
        "auto": REVEAL_ONLY,
        "prefer_tags": ["cao cấp", "tối giản", "ánh sáng"],
        "exclude": [], "overrides": {},
        "note": "PHALEDO: premium, quiet luxury — ánh sáng mềm, reveal chậm. Shop phaledo + 2 shop TikTok mượn qua "
                "templates_from.",
    },
}
WATERMARK = {  # watermark động thay chữ (giữ nguyên enabled/opacity/text/period cũ làm dự phòng khi job không bật motion)
    "giadungplus_official": {"motion": "gdp-ghost-smile", "motion_params": {"hold": 0.13}, "motion_width_pct": 0.13},
    "lteng_vn": {"motion": "lteng-ghost-signature", "motion_params": {"hold": 0.13}, "motion_width_pct": 0.3},
    "lteng_hcm": {"motion": "lteng-ghost-signature", "motion_params": {"hold": 0.15}, "motion_width_pct": 0.26},
    "phaledo_official": {"motion": "phaledo-refraction-sweep", "hold_at": 2.45, "settle": 1.2, "motion_width_pct": 0.36},
    "phaledo": {"motion": "phaledo-refraction-sweep", "hold_at": 2.45, "settle": 1.2, "motion_width_pct": 0.36},
}


def main() -> None:
    for shop in sorted(set(MOTION) | set(WATERMARK)):
        p = SHOPS / shop / "shop.json"
        prof = json.loads(p.read_text(encoding="utf-8"))
        if shop in MOTION:
            prof["motion"] = MOTION[shop]
        if shop in WATERMARK:
            wm = prof.setdefault("watermark", {})
            wm.update(WATERMARK[shop])
            wm["note_motion"] = ("Sếp 23/10: watermark chữ → animation (job khai edl.motion). Không có edl.motion → "
                                 "vẫn watermark chữ như cũ.")
        p.write_text(json.dumps(prof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{shop}: motion={'có' if shop in MOTION else 'mượn templates_from'} · watermark động "
              f"{WATERMARK.get(shop, {}).get('motion', '-')}")


if __name__ == "__main__":
    main()
