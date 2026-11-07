"""Phong cách dựng (Style Pack) — assets/styles/<id>/style.json (Sếp 07/11, học cách "Skill Edit Video Pro" đóng gói
s1 / m2 / Blue 1: MỘT lõi dựng, nhiều "bộ hình").

Một phong cách khai: kiểu chữ động (skin cho assets/kinetic/<page>), cao độ / vị trí chữ, chỉnh màu, nền màn chữ,
theme ưu tiên cho Scene Library, Scene nên dùng / tránh, nhịp cắt lời, mức nhạc. cut.py chỉ cần:

    c.style("gdp-ban-hang")        # trước c.say(); c.logo(shop) quyết định màu nhấn / font theo thương hiệu

Font + màu nhấn LUÔN theo thương hiệu của shop (GDP: UTM Avo · PHALEDO: Averta, không serif — luật đã chốt), phong
cách chỉ đổi cách dùng. Xem danh sách: `vs.py styles`.
"""

import json
from pathlib import Path

from studio import config

STYLES = config.ROOT / "assets" / "styles"
FONT_BY_BRAND = {"GIADUNGPLUS": "avo", "LTENG": "avo", "PHALEDO": "averta"}   # theo shop.json "fonts.rule"


class StyleError(ValueError):
    pass


def ids() -> list[str]:
    return sorted(p.parent.name for p in STYLES.glob("*/style.json"))


def load(style_id: str) -> dict:
    p = STYLES / style_id / "style.json"
    if not p.exists():
        raise StyleError(f"Không có phong cách '{style_id}' (có: {', '.join(ids())})")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["dir"] = str(p.parent)
    return d


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _shop(shop: str | None) -> dict:
    if not shop:
        return {}
    try:
        from studio.templates import shop_profile
        return shop_profile(shop) or {}
    except Exception:   # shop chưa cấu hình → màu mặc định của phong cách
        return {}


def resolve(style: dict, shop: str | None) -> dict:
    """Phong cách + shop → cấu hình dựng cụ thể: skin chữ động (font, màu nhấn theo brand), cao độ chữ, theme Scene."""
    sp = _shop(shop)
    brand = sp.get("brand") or "*"
    pal = sp.get("palette") or {}
    skin = json.loads(json.dumps(style.get("skin", {})))
    by_brand = (style.get("skin_by_brand") or {}).get(brand) or {}
    skin.update(by_brand)
    skin.setdefault("font", FONT_BY_BRAND.get(brand, "averta"))
    accent = skin.get("accent") or pal.get("accent") or "#ffd23f"
    skin["accent"] = accent
    # chữ trên hộp nhấn: tối trên nền sáng, trắng trên nền tối (LTENG xanh đậm → chữ trắng)
    skin.setdefault("boxText", "#141414" if _lum(accent) > 0.45 else "#ffffff")
    themes = style.get("scene_theme") or {}
    return {"id": style["id"], "name": style.get("name", style["id"]), "page": style.get("kinetic", "cinematic"),
            "skin": skin, "captions": style.get("captions", {}), "grade": style.get("grade", "cinematic"),
            "card_bg": style.get("card_bg", "black"), "pacing": style.get("pacing", {}),
            "audio": style.get("audio", {}), "brand": brand,
            "scene_theme": themes.get(brand, themes.get("*")),
            "scenes": style.get("scenes", {})}


def prefers_theme(cfg: dict | None, prof: dict) -> str | None:
    """Theme Scene theo phong cách nếu family có theme đó (family cũ chỉ có theme thương hiệu → None = như cũ)."""
    if not cfg:
        return None
    th = cfg.get("scene_theme")
    if isinstance(th, list):
        return next((t for t in th if t in prof["themes"]), None)
    return th if th in prof["themes"] else None


def summary() -> list[dict]:
    out = []
    for i in ids():
        s = load(i)
        out.append({"id": i, "name": s.get("name", i), "learned_from": s.get("learned_from", ""),
                    "use_for": s.get("use_for", []), "status": s.get("status", "ready")})
    return out
