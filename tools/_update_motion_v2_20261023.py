"""Một lần (23/10/2026, Motion Director V2): chỗ đặt/cỡ animation theo tỉ lệ khung + vai trò thêm (accent), cấu hình
shop: logo thường trực V2, budget AUTO theo thời lượng, vòng đời watermark. Không sửa nguồn animation (src/)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import motionlib as ml  # noqa: E402
from studio.templates import SHOPS  # noqa: E402

TOP = {"y": "top", "margin_y_pct": 0.03}
ANIM = {
    # GDP Roll & Smile: logo dựng ở trái-trên, lăn vào TỪ MÉP TRÁI video; vùng thấy được cắt ở x ≤ 780 (khung thiết kế)
    # → không lăn ngang cả khung; dừng ở 3,3s (logo đầy đủ) rồi mờ ra cho logo thường trực tiếp quản.
    "gdp-roll-smile": {"params": {"x": 360, "y": 960, "size": 440},
                       "placement": {**TOP, "x": "left", "margin_x_pct": 0, "region": [0, None, 780, None],
                                     "feather_px": 80, "width_pct": {"9:16": 0.52, "3:4": 0.5, "1:1": 0.42, "16:9": 0.3},
                                     "play_until": 3.3, "fade_out": 0.3, "handoff": 0.3}},
    "gdp-orbit-settle": {"params": {"format": "9x16", "anchor": "center", "scale": 0.7},
                         "placement": {**TOP, "x": "left", "margin_x_pct": 0,
                                       "width_pct": {"9:16": 0.46, "3:4": 0.44, "1:1": 0.38, "16:9": 0.26},
                                       "handoff": 0.4}},
    "gdp-peek-a-boo": {"roles": ["accent", "micro_animation"],
                       "placement": {"margin_x_pct": 0, "width_pct": {"9:16": 0.11, "3:4": 0.11, "1:1": 0.09, "16:9": 0.07},
                                     "candidates": [{"params": {"side": "left"}, "x": "left", "y": 0.36},
                                                    {"params": {"side": "right"}, "x": "right", "y": 0.36},
                                                    {"params": {"side": "left"}, "x": "left", "y": 0.56},
                                                    {"params": {"side": "right"}, "x": "right", "y": 0.56}]}},
    "lteng-precision-assembly": {"placement": {**TOP, "x": "logo_side",
                                               "width_pct": {"9:16": 0.38, "3:4": 0.36, "1:1": 0.32, "16:9": 0.22},
                                               "handoff": 0.4}},
    "lteng-rail-glide": {"placement": {**TOP, "x": "logo_side",
                                       "width_pct": {"9:16": 0.34, "3:4": 0.32, "1:1": 0.28, "16:9": 0.2}, "handoff": 0.4}},
    "lteng-magenta-signal": {"roles": ["brand_reveal", "accent"],
                             "placement": {**TOP, "x": "logo_side",
                                           "width_pct": {"9:16": 0.3, "3:4": 0.3, "1:1": 0.26, "16:9": 0.18},
                                           "handoff": 0.3},
                             "placement_by_role": {"accent": {"x": "center", "width_pct": {"9:16": 0.26, "3:4": 0.26, "16:9": 0.16},
                                                              "candidates": [{"y": 0.42}, {"y": 0.58}]}}},
    "phaledo-crystal-aperture": {"roles": ["brand_reveal", "accent"],
                                 "placement": {"y": "top", "margin_y_pct": 0.025, "x": "logo_side",
                                               "width_pct": {"9:16": 0.27, "3:4": 0.26, "1:1": 0.22, "16:9": 0.16},
                                               "handoff": 0.5},
                                 "placement_by_role": {"accent": {"x": "center", "width_pct": {"9:16": 0.3, "3:4": 0.28, "16:9": 0.18},
                                                                  "candidates": [{"y": 0.42}, {"y": 0.6}]}}},
    "phaledo-refraction-sweep": {"roles": ["brand_reveal", "accent"],
                                 "placement": {"y": "top", "margin_y_pct": 0.025, "x": "logo_side",
                                               "width_pct": {"9:16": 0.36, "3:4": 0.34, "1:1": 0.3, "16:9": 0.22},
                                               "handoff": 0.4},
                                 "placement_by_role": {"accent": {"x": "center", "width_pct": {"9:16": 0.4, "3:4": 0.38, "16:9": 0.24},
                                                                  "candidates": [{"y": 0.42}, {"y": 0.6}]}}},
}
ACCENT_ROLES = ["accent", "micro_animation", "corner_signature"]
REVEAL = {"budget": [[None, 1]], "window": [0.3, 0.45], "prefer": "early", "brand_mention": True}
SHOP = {
    "giadungplus_official": {
        "persistent": {"width_pct": {"9:16": 0.16, "3:4": 0.15, "1:1": 0.13, "16:9": 0.1}},
        "auto": {"brand_reveal": REVEAL, "accent": {"roles": ACCENT_ROLES, "budget": [[15, 1], [30, 1], [60, 2]],
                                                    "per_extra_30s": 1, "window": [2.0, 0.92], "prefer": "middle"}},
        "min_gap": 2.5, "life": {"hold": 9, "dim": 0.8, "relocate": True}},
    "lteng_vn": {
        "persistent": {"width_pct": {"9:16": 0.2, "3:4": 0.19, "1:1": 0.17, "16:9": 0.12}},
        "auto": {"brand_reveal": REVEAL, "accent": {"roles": ACCENT_ROLES, "budget": [[15, 1], [30, 1], [60, 2]],
                                                    "per_extra_30s": 1, "window": [2.0, 0.92], "prefer": "middle"}},
        "min_gap": 2.5, "life": {"hold": 10, "dim": 0.8, "relocate": True}},
    "lteng_hcm": {
        "persistent": {"width_pct": {"9:16": 0.19, "3:4": 0.18, "1:1": 0.16, "16:9": 0.11}},
        "auto": {"brand_reveal": REVEAL, "accent": {"roles": ACCENT_ROLES, "budget": [[15, 1], [30, 1], [60, 2]],
                                                    "per_extra_30s": 1, "window": [2.0, 0.92], "prefer": "middle"}},
        "min_gap": 2.5, "life": {"hold": 10, "dim": 0.8, "relocate": True}},
    "phaledo_official": {  # quiet luxury: ít chuyển động — accent chỉ từ video ≥ 30s, cách nhau xa
        "persistent": {"width_pct": {"9:16": 0.21, "3:4": 0.2, "1:1": 0.18, "16:9": 0.13}},
        "auto": {"brand_reveal": REVEAL, "accent": {"roles": ACCENT_ROLES, "budget": [[30, 0], [60, 1]],
                                                    "per_extra_30s": 0.5, "window": [4.0, 0.9], "prefer": "middle"}},
        "min_gap": 5.0, "life": {"hold": 12, "dim": 1.2, "relocate": True}},
}
SHOP_ALIAS = {"phaledo": "phaledo_official"}  # shop phaledo: motion mượn qua templates_from; logo + watermark khai riêng


def main() -> None:
    for aid, upd in ANIM.items():
        a = ml.get(aid)
        p = a["dir"] / "motion.json"
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta.update(upd)
        p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{aid}: vai trò {meta['roles']} · chỗ đặt V2")
    for shop in ("giadungplus_official", "lteng_vn", "lteng_hcm", "phaledo_official", "phaledo"):
        cfg = SHOP[SHOP_ALIAS.get(shop, shop)]
        p = SHOPS / shop / "shop.json"
        prof = json.loads(p.read_text(encoding="utf-8"))
        prof["logo"]["persistent"] = {**cfg["persistent"], "margin_x_pct": 0.04, "margin_y_pct": 0.03,
                                      "note": "Logo thường trực V2 (job bật edl.motion): bề rộng phần logo thấy được / "
                                              "bề rộng khung theo tỉ lệ; lề trên 3% chiều cao, lề ngang 4% bề rộng."}
        if shop in SHOP:
            prof["motion"].update({"auto": cfg["auto"], "min_gap": cfg["min_gap"]})
        prof["watermark"]["lifecycle"] = {"relocate_mode": "slide", "settle_pause": 1.0, **cfg["life"], "fade": 0.4,
                                          "exit": 0.4, "after_reveal": 1.0}  # Sếp 23/10: trượt đổi chỗ như cũ
        p.write_text(json.dumps(prof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{shop}: logo thường trực {cfg['persistent']['width_pct']} · watermark giữ {cfg['life']['hold']}s")


if __name__ == "__main__":
    main()
