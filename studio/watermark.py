"""Watermark chống lấy cắp (Sếp 20/10): chữ thương hiệu MỜ, TRÔI qua nhiều vị trí vùng giữa khung, né ô chữ + góc logo.

Thực tế: KHÔNG watermark nhìn thấy nào chống được tuyệt đối (công cụ xoá chữ AI vẫn xoá được). Mục tiêu là LÀM KHÓ:
dán 1 logo tĩnh hay cắt bỏ 1 góc không che hết; muốn xoá phải bám theo từng khung + vẽ lại nền. Không gây khó chịu:
độ mờ ~12–15%, đổi chỗ êm (smoothstep 1,4s) mỗi ~6s, tránh chỗ đang có ô chữ, không đặt trên outro.
Cấu hình: shop.json watermark {enabled, opacity, text, period} (mặc định theo brand kit prod); edl.watermark ghi đè.
Watermark ĐỘNG (Sếp 23/10 — job bật edl.motion): animation của shop (shop.json watermark.motion): XUẤT HIỆN → CHÌM DẦN
→ ĐỔI CHỖ như watermark chữ cũ (trượt êm mỗi ~6s, chỉ bắt đầu sau khi đã chìm xong) → mờ hẳn trước outro. Tuỳ chọn
`relocate_mode: "fade"`: giữ lâu rồi mờ ra/hiện lại chỗ mới. `schedule_v2` chọn chỗ từng chặng; motiondirector dựng
filter. Không bao giờ 2 watermark.
Job không bật motion: watermark chữ trôi như cũ (`plan`), không đổi gì.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio import config
from studio.templates import SHOPS, shop_profile

MOVE = 1.4  # giây chuyển chỗ


def _inter(a: tuple, b: tuple) -> int:
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def _make_png(shop: str, prof: dict, cfg: dict, W: int, out: Path) -> Image.Image:
    custom = SHOPS / shop / "watermark" / "watermark.png"
    if custom.exists():
        img = Image.open(custom).convert("RGBA")
        tw = round(W * cfg.get("width_pct", 0.4))
        img = img.resize((tw, round(img.height * tw / img.width)), Image.LANCZOS)
    else:
        text = cfg.get("text") or prof.get("title") or shop
        font_rel = (prof.get("fonts") or {}).get("heading")
        font_path = config.FONTS / font_rel if font_rel else config.FONT_BOLD
        target_w = round(W * cfg.get("width_pct", 0.4))
        size = 20
        while True:  # cỡ chữ để chữ rộng ≈ target_w
            f = ImageFont.truetype(str(font_path), size)
            if f.getlength(text) >= target_w or size > 400:
                break
            size += 2
        pad = max(4, size // 6)
        box = f.getbbox(text, stroke_width=pad // 2)
        img = Image.new("RGBA", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((pad - box[0], pad - box[1]), text, font=f, fill=(255, 255, 255, 255),
                                 stroke_width=max(1, pad // 3), stroke_fill=(0, 0, 0, 200))
    alpha = img.getchannel("A").point(lambda a: round(a * float(cfg.get("opacity", 0.14))))
    img.putalpha(alpha)
    img.save(out)
    return img


def _smooth(a: float, b: float, t0: float) -> str:
    """Biểu thức ffmpeg: đi từ a tới b trong MOVE giây bắt đầu t0 (smoothstep)."""
    u = f"min(1,max(0,(t-{t0:.3f})/{MOVE}))"
    return f"({a:.1f}+({b - a:.1f})*{u}*{u}*(3-2*{u}))"


def candidates(W: int, H: int, ww: int, wh: int) -> list[tuple[int, int]]:
    """Lưới 2 cột × 4 hàng trong vùng giữa (chừa đỉnh 10% và đáy 14% — logo + phụ đề hay nằm đó)."""
    cands = []
    for cx in (0.30, 0.70):
        for cy in (0.22, 0.38, 0.54, 0.70):
            x = min(max(0, round(W * cx - ww / 2)), W - ww)
            y = min(max(0, round(H * cy - wh / 2)), H - wh)
            cands.append((x, y))
    return cands


def schedule_v2(W: int, H: int, ww: int, wh: int, start: float, settle_end: float, main_dur: float, life: dict,
                avoid: list[dict], busy=None, seed: str = "") -> dict:
    """Các chặng chỗ đứng của watermark động. Chặng 1 luôn chứa trọn INTRO + chìm dần (không đổi chỗ khi chưa chìm xong).
      relocate_mode "slide" (mặc định — Sếp 23/10 "như cũ"): sau khi chìm xong, TRƯỢT êm sang chỗ mới mỗi `period` giây
        (giống watermark chữ trôi cũ); lần trượt đầu ở max(chìm xong + settle_pause, vào + period).
      relocate_mode "fade": giữ `hold` giây rồi mới đổi chỗ, mờ ra chỗ cũ / hiện ở chỗ mới; chặng sau ≥ 0,6×hold.
    avoid = vùng chữ/logo/animation theo thời gian; busy(rect,t0,t1) → (độ rối, độ sáng) để né sản phẩm.
    Trả {segments:[{start,end,x,y,cost}], relocations:[t], mode}."""
    mode = life.get("relocate_mode", "slide")
    cands = candidates(W, H, ww, wh)
    rng = random.Random(seed)
    if mode == "slide":
        period = float(life.get("period", 6.0))
        bounds = [start, min(main_dur, max(settle_end + float(life.get("settle_pause", 1.0)), start + period))]
        if life.get("relocate", True):
            while main_dur - bounds[-1] >= 2.0:  # còn < 2s thì thôi trượt (vừa tới chỗ mới đã hết video)
                bounds.append(min(main_dur, bounds[-1] + period))
    else:
        hold = float(life.get("hold", 10.0))
        bounds = [start, min(main_dur, settle_end + hold)]
        if life.get("relocate", True):
            while main_dur - bounds[-1] >= 0.6 * hold + 1e-6:
                bounds.append(min(main_dur, bounds[-1] + hold))
    if bounds[-1] < main_dur:
        bounds[-1] = main_dur
    segs = []
    for t0, t1 in zip(bounds[:-1], bounds[1:]):
        def cost(p: tuple) -> float:
            r = (p[0], p[1], ww, wh)
            c = sum(_inter(r, (b["x"], b["y"], b["w"], b["h"])) * max(0.0, min(b["end"], t1) - max(b["start"], t0))
                    for b in avoid) / (ww * wh * max(0.1, t1 - t0))
            if busy:
                c += 0.5 * busy(r, t0, t1)[0]
            if segs and p == (segs[-1]["x"], segs[-1]["y"]):
                c += 100  # đã đổi chặng thì phải đổi chỗ thật
            return c
        best = min(cands, key=lambda p: (round(cost(p), 3), rng.random()))  # hoà điểm → ngẫu nhiên cố định theo job
        segs.append({"start": round(t0, 3), "end": round(t1, 3), "x": best[0], "y": best[1], "cost": round(cost(best), 4)})
    return {"segments": segs, "relocations": [s["start"] for s in segs[1:]], "mode": mode}


def plan(job_dir: Path, edl: dict, meta: dict, boxes: list[dict], logo_rect: tuple | None) -> dict | None:
    shop = edl.get("shop")
    if not shop:
        return None
    prof = shop_profile(shop)
    cfg = {**(prof.get("watermark") or {}), **(edl.get("watermark") or {})}
    if not cfg.get("enabled"):
        return None
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    img = _make_png(shop, prof, cfg, W, job_dir / "watermark.png")
    ww, wh = img.size
    # ứng viên: lưới 2 cột × 4 hàng trong vùng giữa (chừa đỉnh 10% và đáy 14% — logo + phụ đề hay nằm đó)
    cands = []
    for cx in (0.30, 0.70):
        for cy in (0.22, 0.38, 0.54, 0.70):
            x = min(max(0, round(W * cx - ww / 2)), W - ww)
            y = min(max(0, round(H * cy - wh / 2)), H - wh)
            cands.append((x, y))
    period = float(cfg.get("period", 6.0))
    rng = random.Random(edl.get("shop", "") + str(meta.get("id", "")))  # cố định theo job, khác nhau giữa các video
    pts, t = [], 0.0
    while t < dur:
        t1 = min(dur, t + period)

        def cost(p: tuple) -> float:
            r = (p[0], p[1], ww, wh)
            c = sum(_inter(r, (b["x"], b["y"], b["w"], b["h"])) * max(0.0, min(b["end"], t1) - max(b["start"], t))
                    for b in boxes)
            if logo_rect:
                c += _inter(r, logo_rect) * (t1 - t)
            if pts and p == pts[-1][1]:
                c += ww * wh * period  # bắt buộc đổi chỗ mỗi chặng
            return c

        ranked = sorted(cands, key=cost)
        best = ranked[0] if cost(ranked[0]) > 0 else rng.choice([p for p in ranked if cost(p) == 0])
        pts.append((t, best))
        t = t1
    # biểu thức từng chặng: giữ chỗ cũ → trượt êm sang chỗ mới đầu mỗi chặng
    ex, ey = str(pts[0][1][0]), str(pts[0][1][1])
    for (t0, p), (_, q) in zip(pts[1:], pts[:-1]):
        ex = f"if(lt(t,{t0:.3f}),{ex},{_smooth(q[0], p[0], t0)})"
        ey = f"if(lt(t,{t0:.3f}),{ey},{_smooth(q[1], p[1], t0)})"
    return {"png": job_dir / "watermark.png", "x": ex, "y": ey, "points": pts, "size": (ww, wh)}
