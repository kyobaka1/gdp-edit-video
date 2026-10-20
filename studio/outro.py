"""Outro theo shop = video Sếp đưa sẵn trong assets/shops/<shop>/outro/ (KHÔNG tự dựng — Sếp chốt 20/10).
Bật cho job bằng edl.outro = {"enabled": true}. Tên file lấy từ shop.json outro.file; không có thì lấy file video
đầu tiên trong thư mục outro/."""

from pathlib import Path

from studio import media
from studio.templates import SHOPS, shop_profile

VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv")


def find_video(shop: str, kind: str = "outro") -> Path | None:
    prof = shop_profile(shop)
    declared = prof.get(kind, {}).get("file")
    if declared and (SHOPS / shop / declared).exists():
        return SHOPS / shop / declared
    folder = SHOPS / shop / kind
    vids = sorted(p for p in folder.glob("*") if p.suffix.lower() in VIDEO_EXT and not p.name.startswith(("_", ".")))
    return vids[0] if vids else None


def plan(edl: dict) -> dict | None:
    o = edl.get("outro")
    if not o or o.get("enabled") is False:
        return None
    shop = edl.get("shop")
    if not shop:
        raise ValueError("edl.outro cần edl.shop")
    path = find_video(shop)
    if path is None:
        raise FileNotFoundError(f"Shop {shop} chưa có video outro — thả file vào assets/shops/{shop}/outro/ "
                                f"(hoặc bỏ edl.outro). Không tự dựng outro.")
    info = media.probe(path)
    return {"path": path, "duration": float(info["duration"]), "has_audio": info["has_audio"]}


def total_duration(edl: dict, meta: dict) -> float:
    p = plan(edl)
    return round(meta["duration"] + (p["duration"] if p else 0.0), 3)
