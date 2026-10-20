"""Logo chính của shop đặt suốt phần video chính (không đè outro). Góc trên-trái / trên-phải do máy chọn theo từng video
(Sếp 20/10: "góc trái, góc phải tuỳ video, bạn tự quyết"); ép tay bằng edl.logo.position.

Chấm điểm mỗi góc: (1) mức chồng lên ô chữ đè + chữ trong cảnh (diện tích giao × thời gian giao) — nặng nhất;
(2) độ rối hình ảnh ở góc (mật độ cạnh Canny trên ~12 khung) — né chi tiết sản phẩm. Điểm thấp hơn thắng.
"""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from studio.templates import SHOPS, shop_profile

WIDTH_PCT = 0.22   # bề rộng logo / bề rộng khung (brand kit prod quy ước logo ảnh 20%)
MARGIN_PCT = 0.03  # cách mép
CORNERS = ("top-left", "top-right")


def _logo_file(shop: str, key: str) -> Path:
    files = shop_profile(shop)["logo"]["files"]
    rel = files.get(key) or files.get("primary")
    if not rel or not (SHOPS / shop / rel).exists():
        raise FileNotFoundError(f"Shop {shop} chưa có logo '{key}' (shop.json logo.files) — thả file vào logo/")
    return SHOPS / shop / rel


def _rect(corner: str, W: int, H: int, lw: int, lh: int) -> tuple[int, int, int, int]:
    m = round(W * MARGIN_PCT)
    x = m if corner.endswith("left") else W - m - lw
    y = m if corner.startswith("top") else H - m - lh
    return x, y, lw, lh


def _inter(a: tuple, b: tuple) -> int:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))


def _busyness(video: Path, rects: dict, duration: float, samples: int = 12) -> dict:
    cap = cv2.VideoCapture(str(video))
    score = {c: 0.0 for c in rects}
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_MSEC, (k + 0.5) / samples * duration * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        edges = cv2.Canny(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 80, 160)
        for c, (x, y, w, h) in rects.items():
            score[c] += float(np.mean(edges[y:y + h, x:x + w] > 0)) / samples
    cap.release()
    return score


def plan(job_dir: Path, edl: dict, meta: dict, boxes: list[dict]) -> dict | None:
    """boxes = [{x,y,w,h,start,end}] các ô chữ đè (đã nới/xoay) + chữ trong cảnh. Trả {png, x, y, corner, reason}."""
    cfg = edl.get("logo")
    if not cfg or cfg.get("enabled") is False:
        return None
    shop = edl["shop"]
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    src = Image.open(_logo_file(shop, cfg.get("file_key", "primary"))).convert("RGBA")
    lw = round(W * cfg.get("width_pct", WIDTH_PCT))
    lh = round(src.height * lw / src.width)
    rects = {c: _rect(c, W, H, lw, lh) for c in CORNERS}

    overlap = {c: sum(_inter(r, (b["x"], b["y"], b["w"], b["h"])) *
                      max(0.0, min(b["end"], dur) - max(b["start"], 0.0)) for b in boxes) / (lw * lh * dur)
               for c, r in rects.items()}
    busy = _busyness(job_dir / meta["source"], rects, dur)
    score = {c: overlap[c] * 10 + busy[c] for c in CORNERS}
    corner = cfg.get("position") or min(CORNERS, key=lambda c: score[c])
    reason = ("ép tay" if cfg.get("position") else
              " · ".join(f"{c}: chồng chữ {overlap[c]:.3f}, rối {busy[c]:.3f}" for c in CORNERS))

    png = job_dir / "logo.png"
    logo = src.resize((lw, lh), Image.LANCZOS)
    opacity = float(cfg.get("opacity", 1.0))
    if opacity < 1:
        alpha = logo.getchannel("A").point(lambda a: round(a * opacity))
        logo.putalpha(alpha)
    logo.save(png)
    x, y, _, _ = rects[corner]
    out = {"png": png, "x": x, "y": y, "w": lw, "h": lh, "corner": corner, "reason": reason}
    (job_dir / "logo.json").write_text(json.dumps({**out, "png": png.name}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
