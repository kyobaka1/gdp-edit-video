"""Outro theo shop: ưu tiên video Sếp đưa (assets/shops/<shop>/outro/outro.mp4); không có thì dựng THẺ toàn khung
từ mẫu `outro` (HTML) của shop. Bật cho job bằng edl.outro = {text, sub, duration?}."""

from pathlib import Path

from studio import media
from studio.templates import SHOPS, manifest, shop_profile


def plan(edl: dict) -> dict | None:
    o = edl.get("outro")
    if not o or o.get("enabled") is False:
        return None
    shop = edl.get("shop")
    if not shop:
        raise ValueError("edl.outro cần edl.shop")
    prof = shop_profile(shop)
    mp4 = SHOPS / shop / prof.get("outro", {}).get("file", "outro/outro.mp4")
    if mp4.exists():
        return {"kind": "video", "path": mp4, "duration": float(media.probe(mp4)["duration"])}
    spec = manifest(shop)["slots"].get("outro")
    if not spec:
        raise FileNotFoundError(f"Shop {shop} không có outro.mp4 và mẫu thẻ 'outro' — thêm một trong hai")
    logo_rel = prof["logo"]["files"].get(spec.get("logo", "primary")) or prof["logo"]["files"].get("primary")
    logo = SHOPS / shop / logo_rel if logo_rel else None
    return {"kind": "card", "duration": float(o.get("duration", spec.get("duration", 3.0))),
            "text": o.get("text", ""), "sub": o.get("sub", ""), "logo": logo if logo and logo.exists() else None}


def total_duration(edl: dict, meta: dict) -> float:
    p = plan(edl)
    return round(meta["duration"] + (p["duration"] if p else 0.0), 3)


def card_png(edl: dict, meta: dict, renderer, out: Path) -> Path:
    p = plan(edl)
    img = renderer.render_card("outro", meta["width"], meta["height"], text=p["text"], sub=p["sub"], logo=p["logo"])
    img.convert("RGB").save(out)
    return out
