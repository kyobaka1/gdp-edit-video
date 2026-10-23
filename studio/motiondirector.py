"""Motion Director V2 — điều phối nhận diện động cho MỘT job (Sếp 23/10): chọn (AUTO) / nhận (MANUAL) animation từ thư
viện (motionlib), đặt chỗ + thời điểm, rồi phối 3 hệ thống không triệt tiêu nhau:

  A. animation (brand_reveal / accent / transition / corner_signature … — vai trò lấy từ motion.json, không cứng tên)
  B. logo THƯỜNG TRỰC ở góc: hiện suốt video chính; chỉ TẠM ẨN trong KHOẢNG animation `replaces: ["logo"]` đang chạy
     (mờ ra khi animation vào, hiện lại trước khi animation hết — chuyển giao 0,15–0,3s). Không có cờ tắt logo cả video.
  C. watermark ĐỘNG: XUẤT HIỆN → CHÌM DẦN → ĐỔI CHỖ (mặc định trượt êm mỗi ~6s như watermark chữ cũ, chỉ sau khi chìm
     xong; tuỳ chọn "fade": đứng lâu rồi mờ ra/hiện lại) → mờ hẳn trước outro.

Quyết định + phiên bản đã chốt + lý do chọn/bỏ từng animation ghi `jobs/<id>/motion_plan.json` → tái lập (tất định theo
job id, không gọi AI). Bật cho job bằng `edl.motion` — KHÔNG khai = flow cũ y nguyên (logo cũ + watermark chữ trôi):
  {"mode": "auto" | "manual" | "off",
   "items": [{"id", "start", "role"?, "variant"?, "placement"?, "params"?, "opacity"?, "z"?}],  # chèn tay
   "watermark": true | false | "<id>",  # true = theo shop.json.watermark.motion · false = watermark chữ cũ
   "keep_logo": false,                    # true = logo thường trực KHÔNG ẩn cả trong lúc animation thay logo chạy
   "update": false}                       # true = bỏ phiên bản đã chốt, dùng bản mới nhất
Luật AUTO / budget / chỗ đặt theo shop: shop.json.motion (assets/motion/README.md).
"""

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio import config, media, watermark
from studio import motionlib as ml
from studio.logo import by_aspect
from studio.templates import shop_profile

DEFAULT_AUTO = {  # khi shop.json.motion không khai `auto`
    "brand_reveal": {"budget": [[None, 1]], "window": [0.3, 0.45], "prefer": "early", "brand_mention": True},
    "accent": {"roles": ["accent", "micro_animation", "corner_signature"], "budget": [[15, 1], [30, 1], [60, 2]],
               "per_extra_30s": 1, "window": [2.0, 0.92], "prefer": "middle"},
}
DEFAULT_GAP = 2.5        # giây tối thiểu giữa 2 sự kiện animation (video không rối)
LOGO_FADE = 0.25         # logo thường trực mờ ra khi animation thay logo bắt đầu
HANDOFF = 0.3            # logo hiện lại trong 0,3s cuối của animation (chuyển giao)
MAX_OVERLAP = 0.04       # tỉ lệ (diện tích × thời gian) animation được phép chồng ô chữ
DARK_LUMA = 118          # độ sáng vùng < ngưỡng → biến thể on_dark
# Watermark động: xuất hiện → chìm dần → đổi chỗ TRƯỢT êm mỗi `period` (= watermark.period của shop, như chữ cũ) — Sếp
# 23/10 giữ kiểu cũ; "fade" = giữ `hold` giây rồi mờ ra/hiện lại chỗ mới (tuỳ chọn).
WM_LIFE = {"relocate_mode": "slide", "settle_pause": 1.0, "hold": 10.0, "dim": 0.8, "relocate": True, "fade": 0.4,
           "exit": 0.4, "after_reveal": 1.0}


class MotionPlanError(ValueError):
    pass


def shop_motion(shop: str, _seen: tuple = ()) -> dict:
    """Cấu hình motion của shop; không khai thì theo shop mượn mẫu (templates_from) — như giọng đọc."""
    prof = shop_profile(shop)
    if prof.get("motion"):
        return prof["motion"]
    nxt = prof.get("templates_from")
    return shop_motion(nxt, _seen + (shop,)) if nxt and nxt not in _seen else {}


def budget(rule: dict, dur: float) -> int:
    """Số lần tối đa / video theo thời lượng: `budget` = [[giới hạn giây | null, số lần], …] (+ `per_extra_30s` sau mốc
    cuối) hoặc `max` cố định. Vd [[15,1],[30,1],[60,2]] + per_extra_30s 1 → video 90s = 2 + 1 = 3."""
    if "budget" not in rule:
        return int(rule.get("max", 1))
    last_lim, last_n = 0.0, 0
    for lim, n in rule["budget"]:
        if lim is None or dur <= lim:
            return int(n)
        last_lim, last_n = float(lim), n
    return int(last_n + math.floor((dur - last_lim) / 30.0 * float(rule.get("per_extra_30s", 0))))


def _inter(a, b) -> int:
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def _even(v: float) -> int:
    return max(2, round(v / 2) * 2)


def layout(info: dict, pl: dict, W: int, H: int, logo_side: str | None = None) -> dict:
    """Đặt clip đã cắt (bbox trên khung thiết kế) lên video W×H. Trả {x, y, w, h, scale, crop, feather}.
      region [x0,y0,x1,y1] (px khung thiết kế, null = không giới hạn): vùng hiển thị TỐI ĐA — cắt clip, mép bị cắt mờ dần
        `feather_px` → chuyển động gói trong vùng nhỏ gần neo (không chạy từ mép xa của cả khung).
      cỡ: `width_pct` (bề rộng phần thấy / bề rộng video; số hoặc theo tỉ lệ {"9:16","3:4","1:1","16:9"}) hoặc `scale`
        (1 = khung thiết kế phủ bề ngang video) · `max_height_pct` khống chế chiều cao.
      x: left | center | right | logo_side (cùng phía logo thường trực) | design | số 0–1 (tâm) — lề `margin_x_pct` (×W)
      y: top | center | bottom | design | số 0–1 (tâm) — lề `margin_y_pct` (×H). `margin_pct` cũ (×W cả 2 trục) vẫn nhận."""
    bx, by, bw, bh = info["bbox"]
    cw, ch = info["canvas"]
    reg = list(pl.get("region") or [None] * 4)
    vx0, vy0 = max(bx, reg[0] if reg[0] is not None else bx), max(by, reg[1] if reg[1] is not None else by)
    vx1 = min(bx + bw, reg[2] if reg[2] is not None else bx + bw)
    vy1 = min(by + bh, reg[3] if reg[3] is not None else by + bh)
    if vx1 - vx0 < 8 or vy1 - vy0 < 8:
        raise MotionPlanError(f"{info['id']}: region {reg} không giao vùng có hình {info['bbox']}")
    crop = None
    feather = {}
    if (vx0, vy0, vx1, vy1) != (bx, by, bx + bw, by + bh):
        cx0, cy0 = (vx0 - bx) // 2 * 2, (vy0 - by) // 2 * 2  # toạ độ trong clip đã cắt theo bbox, chẵn cho yuv
        crop = [cx0, cy0, min(bw - cx0, vx1 - bx - cx0) // 2 * 2, min(bh - cy0, vy1 - by - cy0) // 2 * 2]
        fp = int(pl.get("feather_px", 48))
        feather = {k: fp for k, cut in (("l", vx0 > bx), ("t", vy0 > by), ("r", vx1 < bx + bw), ("b", vy1 < by + bh)) if cut}
        vw, vh = crop[2], crop[3]
    else:
        vw, vh = bw, bh
    wp = by_aspect(pl.get("width_pct"), W, H)
    s = (float(wp) * W / vw) if wp else (W / cw * float(by_aspect(pl.get("scale", 1.0), W, H)))
    mh = by_aspect(pl.get("max_height_pct"), W, H)
    if mh and vh * s > float(mh) * H:
        s = float(mh) * H / vh
    w, h = _even(vw * s), _even(vh * s)
    if "margin_pct" in pl and "margin_x_pct" not in pl and "margin_y_pct" not in pl:
        mx = my = round(W * float(pl["margin_pct"]))
    else:
        mx, my = round(W * float(pl.get("margin_x_pct", 0.04))), round(H * float(pl.get("margin_y_pct", 0.035)))
    X, Y = pl.get("x", "design"), pl.get("y", "design")
    if X == "logo_side":
        X = logo_side or "left"
    if X == "design":
        x = (W - cw * s) / 2 + vx0 * s
    elif X == "left":
        x = mx
    elif X == "right":
        x = W - mx - w
    elif X == "center":
        x = (W - w) / 2
    else:
        x = float(X) * W - w / 2
    if Y == "design":
        y = (vy0 + vh / 2) / ch * H - h / 2
    elif Y == "top":
        y = my
    elif Y == "bottom":
        y = H - my - h
    elif Y == "center":
        y = (H - h) / 2
    else:
        y = float(Y) * H - h / 2
    if X != "design":
        x = min(max(0, x), W - w)
    if Y != "design":
        y = min(max(0, y), H - h)
    return {"x": round(x), "y": round(y), "w": w, "h": h, "scale": round(s, 4), "crop": crop, "feather": feather}


def place(info: dict, pl: dict, W: int, H: int) -> tuple[int, int, int, int]:
    """Giữ tương thích: chỉ trả (x, y, w, h)."""
    L = layout(info, pl, W, H)
    return L["x"], L["y"], L["w"], L["h"]


class Footage:
    """Khung nguồn lấy mẫu thưa (mỗi 0,5s, thu nhỏ): độ rối (cạnh Canny ≈ sản phẩm/tay/chi tiết), độ sáng (chọn biến thể
    màu), mốc chuyển cảnh (khác biệt lớn giữa 2 mẫu liền nhau). Đọc 1 lần / job, không gọi AI."""

    def __init__(self, video: Path, duration: float, W: int, step: float = 0.5, width: int = 360):
        self.k = width / W
        self.samples: list[tuple[float, np.ndarray, np.ndarray]] = []
        cap = cv2.VideoCapture(str(video))
        t = step / 2
        while t < duration:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, fr = cap.read()
            if ok:
                g = cv2.cvtColor(cv2.resize(fr, (width, round(fr.shape[0] * width / fr.shape[1]))), cv2.COLOR_BGR2GRAY)
                self.samples.append((t, g, cv2.Canny(g, 80, 160) > 0))
            t += step
        cap.release()
        self.cuts = [round((a[0] + b[0]) / 2, 2) for a, b in zip(self.samples, self.samples[1:])
                     if float(np.abs(a[1].astype(np.int16) - b[1].astype(np.int16)).mean()) > 28]

    def stats(self, rect, t0: float, t1: float) -> tuple[float, float]:
        x, y, w, h = (round(v * self.k) for v in rect)
        sel = [s for s in self.samples if t0 <= s[0] <= t1] or \
              ([min(self.samples, key=lambda s: abs(s[0] - (t0 + t1) / 2))] if self.samples else [])
        if not sel:
            return 0.0, 128.0
        busy = luma = 0.0
        for _, g, e in sel:
            gy0, gx0 = max(0, y), max(0, x)
            reg_e, reg_g = e[gy0:y + h, gx0:x + w], g[gy0:y + h, gx0:x + w]
            if reg_g.size:
                busy += float(reg_e.mean())
                luma += float(reg_g.mean())
        return busy / len(sel), luma / len(sel)


def _overlap(rect, boxes: list[dict], t0: float, t1: float) -> float:
    area = rect[2] * rect[3] * max(1e-3, t1 - t0)
    return sum(_inter(rect, (b["x"], b["y"], b["w"], b["h"])) * max(0.0, min(b["end"], t1) - max(b["start"], t0))
               for b in boxes) / area


def _jitter(job_id: str, anim_id: str) -> float:
    return int(hashlib.sha1(f"{job_id}:{anim_id}".encode()).hexdigest()[:4], 16) / 65535


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def _sibling_used(job_dir: Path, meta: dict) -> set[str]:
    """Animation các bản khác CÙNG video nguồn đã dùng (đa dạng giữa shop — như luật thuyết minh)."""
    used = set()
    origin = Path(meta.get("origin", "")).name
    for j in job_dir.parent.iterdir():
        mp, mt = j / "motion_plan.json", j / "meta.json"
        if j == job_dir or not mp.exists() or not mt.exists():
            continue
        try:
            if Path(json.loads(mt.read_text(encoding="utf-8")).get("origin", "")).name == origin:
                used |= {it["id"] for it in json.loads(mp.read_text(encoding="utf-8")).get("items", [])}
        except (json.JSONDecodeError, OSError):
            continue
    return used


class _Ctx:
    def __init__(self, job_dir, edl, meta, boxes, logo_rect):
        self.job_dir, self.edl, self.meta, self.boxes = job_dir, edl, meta, boxes
        self.W, self.H, self.dur = meta["width"], meta["height"], meta["duration"]
        self.shop = edl.get("shop") or ""
        self.brand = shop_profile(self.shop).get("brand", "") if self.shop else ""
        self.cfg = shop_motion(self.shop) if self.shop else {}
        m = edl.get("motion")
        self.m = {"mode": m} if isinstance(m, str) else ({"mode": "off"} if m is False else dict(m or {}))
        self.logo_rect = logo_rect
        self.logo_side = None if not logo_rect else ("left" if logo_rect[0] + logo_rect[2] / 2 < self.W / 2 else "right")
        self.pinned = {}  # id → src_hash đã chốt ở lần dựng trước (phiên bản job dùng)
        prev = job_dir / "motion_plan.json"
        if prev.exists() and not self.m.get("update"):
            try:
                old = json.loads(prev.read_text(encoding="utf-8"))
                for it in old.get("items", []) + [old.get("watermark") or {}]:
                    if it.get("id") and it.get("src_hash"):
                        self.pinned[it["id"]] = it["src_hash"]
            except json.JSONDecodeError:
                pass
        self._footage = None
        self.wm_proto: dict | None = None  # watermark động đã giải (animation, khung giữ, độ dài intro)
        self.notes: list[str] = []
        self.warnings: list[str] = []
        self.skipped: dict[str, str] = {}
        self.mentions = self._brand_mentions()
        self.pauses = self._narration_pauses()

    def _brand_mentions(self) -> list[float]:
        """Giây bắt đầu các đoạn thuyết minh có nhắc tên thương hiệu (brand / tên shop) — chỗ hợp cho brand reveal."""
        p = self.job_dir / "narration.json"
        if not p.exists() or not self.shop:
            return []
        prof = shop_profile(self.shop)
        keys = {_norm(k) for k in (self.brand, prof.get("title", ""), *prof.get("aliases", [])) if len(_norm(k)) >= 4}
        try:
            pieces = json.loads(p.read_text(encoding="utf-8")).get("pieces", [])
        except json.JSONDecodeError:
            return []
        return [float(x["start"]) for x in pieces if any(k in _norm(x.get("text", "")) for k in keys)]

    def _narration_pauses(self) -> list[tuple[float, float]]:
        p = self.job_dir / "narration.json"
        if not p.exists():
            return []
        try:
            pieces = sorted(json.loads(p.read_text(encoding="utf-8")).get("pieces", []), key=lambda x: x["start"])
        except json.JSONDecodeError:
            return []
        out, prev = [], 0.0
        for x in pieces:
            if x["start"] - prev >= 0.6:
                out.append((prev, float(x["start"])))
            prev = float(x["end"])
        return out

    @property
    def footage(self) -> Footage:
        if self._footage is None:
            self._footage = Footage(self.job_dir / self.meta["source"], self.dur, self.W)
        return self._footage

    def override(self, anim_id: str) -> dict:
        return (self.cfg.get("overrides") or {}).get(anim_id) or {}

    def placement(self, a: dict, role: str, extra: dict | None = None) -> dict:
        """Thứ tự: mặc định vai trò của shop < placement của animation < placement theo vai trò < override shop < chèn tay."""
        pl = {**((self.cfg.get("defaults") or {}).get(role, {}).get("placement") or {}), **a["placement"],
              **((a.get("placement_by_role") or {}).get(role) or {}), **(self.override(a["id"]).get("placement") or {}),
              **(extra or {})}
        return pl

    def render(self, a: dict, variant=None, params=None) -> dict:
        """Render (cache) có tôn trọng phiên bản đã chốt của job."""
        cur = ml.source_hash(a)
        pin = self.pinned.get(a["id"])
        if pin and pin != cur:
            spec = ml.spec_for(a, variant, params)
            hit = ml.find_cached(a["id"], ml.cache_key(pin, spec))
            if hit:
                self.notes.append(f"{a['id']}: dùng phiên bản ĐÃ CHỐT {pin[:8]} (thư viện đã có bản mới "
                                  f"{cur[:8]}; muốn lên bản mới: edl.motion.update=true)")
                return hit
            old = ml.archived_source(a, pin)
            if old:
                self.notes.append(f"{a['id']}: render lại phiên bản đã chốt {pin[:8]} từ _versions/")
                return ml.render(old, variant, params, src_hash=pin)
            raise MotionPlanError(f"{a['id']}: job đã chốt phiên bản {pin[:8]} nhưng thư viện không còn bản đó "
                                  f"(cache + _versions) — đặt edl.motion.update=true để dùng bản hiện tại {cur[:8]}")
        return ml.render(a, variant, params, src_hash=cur)


def _check_anim(ctx: _Ctx, anim_id: str, force: bool = False) -> dict:
    try:
        a = ml.get(anim_id)
    except ml.MotionError as exc:
        raise MotionPlanError(str(exc))
    if not ml.applies_to(a, ctx.shop, ctx.brand):
        raise MotionPlanError(f"Animation '{anim_id}' (brand {', '.join(a['brands']) or a.get('shop_scope')}) KHÔNG dùng "
                              f"cho shop {ctx.shop} (brand {ctx.brand}) — chọn animation đúng brand")
    if a["problems"]:
        raise MotionPlanError(f"Animation '{anim_id}' chưa hợp lệ: " + "; ".join(a["problems"]))
    if not a["enabled"] and not force:
        raise MotionPlanError(f"Animation '{anim_id}' đang TẮT (vs.py motion enable {anim_id}) — hoặc \"force\": true")
    return a


def _want_variant(a: dict, luma: float) -> str | None | bool:
    """Biến thể màu theo độ sáng vùng đặt. Không khai biến thể = dùng mọi nền. False = thiếu tương phản (không có bản hợp)."""
    if not a["variants"]:
        return None
    want = "on_dark" if luma < DARK_LUMA else "on_light"
    if want in a["variants"]:
        return want
    if not ({"on_dark", "on_light"} & set(a["variants"])):
        return a.get("default_variant")
    return False


def _item(ctx: _Ctx, a: dict, info: dict, L: dict, start: float, pl: dict, role: str, reason: str, **kw) -> dict:
    play = pl.get("play_until")
    clip = min(info["duration"], float(play)) if play else info["duration"]
    end = min(ctx.dur, start + clip)
    if start + clip > ctx.dur + 0.05:
        ctx.warnings.append(f"{a['id']}: dài {clip:.2f}s nhưng chỉ còn {ctx.dur - start:.2f}s trước outro → bị cắt")
    rect = (L["x"], L["y"], L["w"], L["h"])
    ov = ctx.override(a["id"])
    return {"id": a["id"], "name": a.get("name"), "version": a["version"], "src_hash": info["src_hash"],
            "key": info["key"], "mov": info["mov"], "role": role, "replaces": list(a["replaces"]),
            "start": round(start, 3), "end": round(end, 3), "x": L["x"], "y": L["y"], "w": L["w"], "h": L["h"],
            "scale": L["scale"], "crop": L["crop"], "feather": L["feather"],
            "play_until": round(clip, 3) if play else None, "fade_out": float(pl.get("fade_out", 0.3)) if play else 0.0,
            "handoff": float(pl.get("handoff", HANDOFF)),
            "opacity": float(kw.get("opacity", ov.get("opacity", 1.0))),
            "z": kw.get("z") or ov.get("z") or a["z"], "variant": info["spec"]["variant"],
            "params": info["spec"]["params"], "placement": {k: v for k, v in pl.items() if k != "candidates"},
            "reason": reason, "overlap": round(_overlap(rect, ctx.boxes, start, end), 4)}


def _manual(ctx: _Ctx, spec: dict) -> dict:
    a = _check_anim(ctx, spec["id"], force=bool(spec.get("force")))
    role = spec.get("role") or (a["roles"] or ["custom"])[0]
    ov = ctx.override(a["id"])
    pl = ctx.placement(a, role, spec.get("placement"))
    pl.pop("candidates", None)
    params = {**(ov.get("params") or {}), **(pl.pop("params", None) or {}), **(spec.get("params") or {})}
    variant = spec.get("variant", ov.get("variant"))
    info = ctx.render(a, variant, params)
    L = layout(info, pl, ctx.W, ctx.H, ctx.logo_side)
    if "variant" not in spec and a["variants"] and variant is None:  # chưa chọn màu → theo độ sáng vùng đặt
        _, luma = ctx.footage.stats((L["x"], L["y"], L["w"], L["h"]), float(spec["start"]),
                                    float(spec["start"]) + info["duration"])
        v = _want_variant(a, luma)
        if v and v != info["spec"]["variant"]:
            info = ctx.render(a, v, params)
            L = layout(info, pl, ctx.W, ctx.H, ctx.logo_side)
    it = _item(ctx, a, info, L, float(spec["start"]), pl, role, "chèn tay (edl.motion.items)",
               opacity=spec.get("opacity", ov.get("opacity", 1.0)), z=spec.get("z"))
    if it["overlap"] > MAX_OVERLAP:
        ctx.warnings.append(f"{a['id']} (chèn tay) chồng ô chữ {it['overlap']:.0%} — đổi placement/start")
    return it


def _events_ok(t0: float, t1: float, taken: list[dict], gap: float) -> bool:
    return all(t1 + gap <= it["start"] or t0 >= it["end"] + gap for it in taken)


def _wm_start(ctx: "_Ctx", items: list[dict], life: dict) -> float:
    """Watermark vào SAU brand reveal mở đầu video (không dồn 2 logo cùng lúc), không thì từ 0."""
    start = 0.0
    for it in items:
        if "logo" in it["replaces"] and it["start"] < 3.0:
            start = max(start, it["end"] + float(life["after_reveal"]))
    return start


def _wm_window(ctx: "_Ctx", items: list[dict]) -> dict | None:
    """Đoạn INTRO + DIM dự kiến của watermark động (sự kiện thương hiệu) — accent phải né để video không rối."""
    p = ctx.wm_proto
    if not p:
        return None
    s = _wm_start(ctx, items, p["life"])
    return {"start": s, "end": s + p["clip"] + p["dim"], "id": "(watermark intro)"}


def _auto_role(ctx: _Ctx, role: str, rule: dict, taken: list[dict], usable: list[dict], reserved: set[str]) -> list[dict]:
    """Chọn animation cho MỘT luật AUTO (vai trò). Ghi lý do bỏ từng ứng viên vào ctx.skipped."""
    pool_roles = set(rule.get("roles") or [role])
    n_max = budget(rule, ctx.dur) - sum(1 for it in taken if it["role"] == role)
    w0, w1 = rule.get("window") or [1.0, 0.6]
    t_lo = float(w0)
    t_hi = float(w1) * ctx.dur if float(w1) <= 1 else float(w1)
    gap = float(ctx.cfg.get("min_gap", DEFAULT_GAP))
    prefer = set(ctx.cfg.get("prefer_tags") or [])
    excl = set(ctx.cfg.get("exclude") or [])
    pool = ctx.cfg.get("pool")
    used = _sibling_used(ctx.job_dir, ctx.meta)
    cands = []
    for a in usable:
        if not pool_roles & set(a["roles"]):
            continue
        if a["id"] in excl or (pool and a["id"] not in pool):
            ctx.skipped.setdefault(a["id"], "shop loại trừ (exclude/pool)")
        elif a["id"] in reserved or any(it["id"] == a["id"] for it in taken):
            continue  # đã dùng (vai trò khác / watermark) — lý do ghi ở chỗ dùng
        else:
            cands.append(a)
    cands.sort(key=lambda a: -(a["priority"] + 10 * len(prefer & set(a["tags"])) - 30 * (a["id"] in used)
                               + 8 * _jitter(ctx.meta.get("id", ctx.job_dir.name), a["id"])))
    if not cands and n_max > 0:
        busy_ids = [a["id"] for a in usable if pool_roles & set(a["roles"])]
        ctx.notes.append(f"AUTO '{role}' (budget {n_max}): không còn ứng viên — "
                         + (", ".join(f"{i} " + ("dùng làm watermark" if i in reserved else "đã dùng vai trò khác")
                                      for i in busy_ids) if busy_ids else f"thư viện shop chưa có animation vai trò "
                                                                          f"{', '.join(sorted(pool_roles))}")
                         + " → không ép thêm")
    out = []
    if n_max <= 0:
        for a in cands:
            ctx.skipped.setdefault(a["id"], f"hết budget '{role}' (video {ctx.dur:.0f}s → {budget(rule, ctx.dur)} lần)")
        return out
    for a in cands:
        if len(out) >= n_max:
            ctx.skipped.setdefault(a["id"], f"hết budget '{role}' ({n_max}/video {ctx.dur:.0f}s)")
            continue
        ov = ctx.override(a["id"])
        base_pl = ctx.placement(a, role)
        pls = base_pl.pop("candidates", None) or [{}]
        avoid = list(ctx.boxes)
        if ctx.logo_rect and "logo" not in a["replaces"]:  # không thay logo → không được đè logo thường trực
            avoid.append({"x": ctx.logo_rect[0], "y": ctx.logo_rect[1], "w": ctx.logo_rect[2], "h": ctx.logo_rect[3],
                          "start": 0.0, "end": ctx.dur})
        avoid += [{"x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"], "start": it["start"], "end": it["end"]}
                  for it in taken + out]
        best, why = None, "không có vị trí/thời điểm trống (chồng chữ > 4% hoặc sát sự kiện khác)"
        for c in pls:
            pl = {**base_pl, **c}
            params = {**(ov.get("params") or {}), **(pl.pop("params", None) or {})}
            try:
                info = ctx.render(a, ov.get("variant"), params)
                L = layout(info, pl, ctx.W, ctx.H, ctx.logo_side)
            except (ml.MotionError, MotionPlanError) as exc:
                why = f"lỗi render/đặt chỗ: {str(exc)[:120]}"
                break
            d = min(info["duration"], float(pl["play_until"])) if pl.get("play_until") else info["duration"]
            if ctx.dur < d + 0.5 or t_hi < t_lo:
                why = f"video quá ngắn cho animation {d:.1f}s"
                continue
            rect = (L["x"], L["y"], L["w"], L["h"])
            events = taken + out
            wmw = _wm_window(ctx, taken + out)
            t = t_lo
            while t + d <= min(ctx.dur - 0.2, t_hi + d) + 1e-6:
                ovl = _overlap(rect, avoid, t, t + d)
                # reveal mở đầu (thay logo, < 3s) tự đẩy watermark vào sau nó → không cần né; còn lại phải né intro watermark
                ev = events + [wmw] if wmw and not ("logo" in a["replaces"] and t < 3.0) else events
                if ovl <= MAX_OVERLAP and _events_ok(t, t + d, ev, gap):
                    busy, luma = ctx.footage.stats(rect, t, t + d)
                    span = max(1.0, t_hi - t_lo)
                    pos = (t - t_lo) / span if rule.get("prefer", "early") == "early" else abs((t + d / 2) - ctx.dur / 2) / (ctx.dur / 2)
                    bonus, tags = 0.0, []
                    if rule.get("brand_mention") and any(m - 0.6 <= t <= m + 1.0 for m in ctx.mentions):
                        bonus += 0.06
                        tags.append("đúng lúc nhắc thương hiệu")
                    if any(t - 0.7 <= c <= t + 0.3 for c in ctx.footage.cuts):
                        bonus += 0.03
                        tags.append("ngay sau chuyển cảnh")
                    if any(p0 <= t + d / 2 <= p1 for p0, p1 in ctx.pauses):
                        bonus += 0.02
                        tags.append("khoảng nghỉ thuyết minh")
                    cost = ovl * 10 + busy + 0.05 * pos - bonus
                    if best is None or cost < best[0]:
                        best = (cost, info, L, t, pl, params, ovl, busy, luma, tags)
                t += 0.5
        if best is None:
            ctx.skipped.setdefault(a["id"], why)
            continue
        cost, info, L, t, pl, params, ovl, busy, luma, tags = best
        v = _want_variant(a, luma) if ov.get("variant") is None else ov["variant"]
        if v is False:
            ctx.skipped.setdefault(a["id"], f"thiếu tương phản: không có biến thể hợp nền (độ sáng vùng {luma:.0f})")
            continue
        if v != info["spec"]["variant"]:
            info = ctx.render(a, v, params)
            L = layout(info, pl, ctx.W, ctx.H, ctx.logo_side)
        it = _item(ctx, a, info, L, t, pl, role,
                   f"AUTO {role}: chồng chữ {ovl:.1%} · rối {busy:.3f} · sáng {luma:.0f} · biến thể {v or 'mặc định'}"
                   + (f" · {', '.join(tags)}" if tags else ""))
        out.append(it)
    return out


def _logo_lifecycle(ctx: _Ctx, items: list[dict]) -> dict:
    """Logo thường trực theo KHOẢNG THỜI GIAN: ẩn chỉ trong lúc animation `replaces: ["logo"]` chạy, có chuyển giao."""
    if not ctx.logo_rect:
        return {"enabled": False, "rect": None, "hidden": [], "visible": [], "reason": "job/shop không bật logo"}
    hidden = []
    if not ctx.m.get("keep_logo"):
        for it in sorted((i for i in items if "logo" in i["replaces"]), key=lambda i: i["start"]):
            a = it["start"] + (LOGO_FADE if it["start"] > 0.05 else 0.0)  # animation mở đầu video → ẩn ngay từ khung 0
            b = it["end"] - it["handoff"]
            if b - a < 0.2:
                continue
            if hidden and a <= hidden[-1][1] + 0.3:  # 2 animation sát nhau → gộp, không nháy logo
                hidden[-1][1] = max(hidden[-1][1], b)
            else:
                hidden.append([round(a, 3), round(b, 3)])
    vis, t = [], 0.0
    for a, b in hidden:
        if a > t:
            vis.append([round(t, 3), round(a, 3)])
        t = b
    if t < ctx.dur:
        vis.append([round(t, 3), round(ctx.dur, 3)])
    shown = sum(b - a for a, b in vis)
    return {"enabled": True, "rect": list(ctx.logo_rect), "hidden": hidden, "visible": vis, "fade_out": LOGO_FADE,
            "fade_in": HANDOFF, "visible_ratio": round(shown / ctx.dur, 3),
            "reason": ("ẩn tạm " + ", ".join(f"{a:.2f}–{b:.2f}s" for a, b in hidden) + " (animation thay logo đang chạy)")
            if hidden else "hiện suốt video chính"}


def _wm_resolve(ctx: _Ctx) -> dict | None:
    """Animation watermark của shop + khung giữ hợp lệ + độ dài intro (dùng trước khi xếp accent để né đoạn intro)."""
    prof = shop_profile(ctx.shop)
    wcfg = {**(prof.get("watermark") or {}), **(ctx.edl.get("watermark") or {})}
    choice = ctx.m.get("watermark", True)
    if not wcfg.get("enabled") or choice is False:
        return None
    wid = choice if isinstance(choice, str) else wcfg.get("motion")
    if not wid:
        return None
    a = _check_anim(ctx, wid)
    life = {**WM_LIFE, "period": float(wcfg.get("period", 6.0)), **(wcfg.get("lifecycle") or {})}
    params = dict(wcfg.get("motion_params") or {})
    variant = wcfg.get("motion_variant")
    if variant is None and a["variants"]:  # màu theo độ sáng vùng giữa cả video
        _, luma = ctx.footage.stats((round(ctx.W * 0.15), round(ctx.H * 0.15), round(ctx.W * 0.7), round(ctx.H * 0.6)),
                                    0, ctx.dur)
        variant = _want_variant(a, luma) or a.get("default_variant")
    info = ctx.render(a, variant, params)
    pose = ml.hold_pose(a, info, wcfg.get("hold_at") if wcfg.get("hold_at") is not None else wcfg.get("hold_time"))
    clip = min(pose["time"] + 1 / info["fps"] if pose["mode"] == "time" else info["duration"], info["duration"])
    dim = float(life["dim"]) if pose["mode"] == "time" else 0.0  # animation tự mờ xuống → không mờ thêm (opacity đúng 1 lần)
    return {"a": a, "wcfg": wcfg, "life": life, "info": info, "pose": pose, "clip": clip, "dim": dim}


def _watermark(ctx: _Ctx, items: list[dict]) -> dict | None:
    """Watermark ĐỘNG V2: INTRO (animation gốc) → SETTLE (khung giữ hợp lệ) → DIM (về opacity mục tiêu, nếu animation
    không tự mờ) → HOLD tại MỘT chỗ → đổi chỗ có điều kiện (mờ ra/hiện lại) → EXIT trước outro."""
    p = ctx.wm_proto
    if not p:
        return None
    a, wcfg, life, info, pose, clip, dim = p["a"], p["wcfg"], p["life"], p["info"], p["pose"], p["clip"], p["dim"]
    wid = a["id"]
    if not pose["ok"]:
        ctx.warnings.append(f"watermark {wid}: khung giữ {pose['time']}s chưa đạt — {'; '.join(pose['problems'])}")
    bw, bh = info["bbox"][2], info["bbox"][3]
    w_pct = by_aspect(wcfg.get("motion_width_pct") or a["placement"].get("width_pct") or wcfg.get("width_pct", 0.2),
                      ctx.W, ctx.H)
    w = _even(ctx.W * float(w_pct))
    h = _even(bh * w / bw)
    start = _wm_start(ctx, items, life)
    if start >= ctx.dur - (clip + dim + 1.0):
        start = 0.0
    settle_end = start + clip + dim
    avoid = list(ctx.boxes) + [{"x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"], "start": it["start"],
                                "end": it["end"]} for it in items]
    if ctx.logo_rect:  # né cả dải dưới logo góc (~15% chiều cao): watermark sát logo nhìn như 2 logo trùng nhau
        lx, ly, lw, lh = ctx.logo_rect
        pad = round(ctx.W * 0.03)
        avoid.append({"x": lx - pad, "y": 0, "w": lw + 2 * pad, "h": ly + lh + round(ctx.H * 0.15),
                      "start": 0.0, "end": ctx.dur})
    sch = watermark.schedule_v2(ctx.W, ctx.H, w, h, start, settle_end, ctx.dur, life, avoid, ctx.footage.stats,
                                seed=ctx.shop + str(ctx.meta.get("id", "")))
    opacity = float(wcfg.get("opacity", 0.14)) if pose["mode"] == "time" else 1.0
    phases = {"intro": [round(start, 3), round(start + clip, 3)],
              "dim": [round(start + clip, 3), round(settle_end, 3)] if dim else None,
              "settled": round(settle_end, 3),  # đã chìm xong — trước mốc này không đổi chỗ
              "hold": [round(settle_end, 3), round(sch["segments"][0]["end"], 3)],
              "relocate": sch["relocations"], "relocate_mode": sch["mode"],
              "exit": [round(max(start, ctx.dur - float(life["exit"])), 3), round(ctx.dur, 3)]}
    return {"id": a["id"], "version": a["version"], "src_hash": info["src_hash"], "key": info["key"], "mov": info["mov"],
            "w": w, "h": h, "clip": round(clip, 4), "start": round(start, 3), "pose": pose, "dim": dim,
            "opacity": opacity, "variant": info["spec"]["variant"], "life": life, "segments": sch["segments"],
            "relocations": sch["relocations"], "phases": phases,
            "reason": f"thay watermark chữ · giữ khung {pose['time']}s ({pose['note']})"
                      + (f" · mờ về {opacity:.0%} trong {dim}s" if dim else " · animation tự mờ xuống")
                      + ((f" · đổi chỗ ({'trượt êm' if sch['mode'] == 'slide' else 'mờ ra/hiện lại'}) lúc "
                          f"{', '.join(f'{r:.1f}s' for r in sch['relocations'])}") if sch["relocations"]
                         else " · giữ 1 chỗ tới hết")}


def plan(job_dir: Path, edl: dict, meta: dict, boxes: list[dict], logo_rect: tuple | None = None) -> dict | None:
    """None = job không khai edl.motion (flow cũ). Trả kế hoạch V2 (xem docstring module) + lý do chọn/bỏ."""
    if "motion" not in edl:
        return None
    ctx = _Ctx(job_dir, edl, meta, boxes, logo_rect)
    mode = ctx.m.get("mode", "auto")
    if mode not in ("auto", "manual", "off"):
        raise MotionPlanError(f"edl.motion.mode '{mode}' không hỗ trợ (auto | manual | off)")
    every = ml.discover()
    usable = ml.catalog(ctx.shop) if ctx.shop else []
    out = {"version": 2, "mode": mode, "shop": ctx.shop, "brand": ctx.brand, "duration": ctx.dur,
           "library": {"total": len(every), "usable": len(usable), "usable_ids": [a["id"] for a in usable]},
           "budget": {}, "items": [], "watermark": None, "logo": None, "skipped": [], "notes": ctx.notes,
           "warnings": ctx.warnings}
    for a in every:
        if ctx.shop and not ml.applies_to(a, ctx.shop, ctx.brand):
            ctx.skipped[a["id"]] = f"sai brand ({', '.join(a['brands']) or a.get('shop_scope')} ≠ {ctx.brand})"
        elif not a["enabled"]:
            ctx.skipped[a["id"]] = "đang tắt" + (f" — {a['disabled_reason']}" if a.get("disabled_reason") else "")
        elif a["problems"]:
            ctx.skipped[a["id"]] = "motion.json lỗi: " + "; ".join(a["problems"])
    items: list[dict] = []
    if mode != "off" and ctx.shop:
        items = [_manual(ctx, s) for s in ctx.m.get("items") or []]
        wid = (ctx.m.get("watermark") if isinstance(ctx.m.get("watermark"), str)
               else (shop_profile(ctx.shop).get("watermark") or {}).get("motion"))
        reserved = {wid} if wid and ctx.m.get("watermark", True) is not False else set()
        ctx.wm_proto = _wm_resolve(ctx)
        if mode == "auto":
            rules = ctx.cfg.get("auto") or DEFAULT_AUTO
            for role, rule in rules.items():
                rule = rule or {}
                out["budget"][role] = budget(rule, ctx.dur)
                items += _auto_role(ctx, role, rule, items, usable, reserved)
            covered = set().union(*[set((r or {}).get("roles") or [k]) for k, r in rules.items()])
            for a in usable:
                if a["id"] not in ctx.skipped and a["id"] not in reserved and not any(i["id"] == a["id"] for i in items) \
                        and not covered & set(a["roles"]):
                    ctx.skipped[a["id"]] = f"vai trò {', '.join(a['roles'])} không có trong luật AUTO của shop (chèn tay được)"
        else:
            for a in usable:
                if not any(i["id"] == a["id"] for i in items) and a["id"] not in reserved:
                    ctx.skipped.setdefault(a["id"], "mode manual: chỉ chèn animation khai trong edl.motion.items")
        items.sort(key=lambda it: it["start"])
        out["items"] = items
        out["watermark"] = _watermark(ctx, items)
        if out["watermark"]:
            ctx.skipped.pop(out["watermark"]["id"], None)
    elif not ctx.shop and mode != "off":
        ctx.warnings.append("edl.motion cần edl.shop — bỏ qua animation")
    out["logo"] = _logo_lifecycle(ctx, items)
    used_ids = {it["id"] for it in items} | ({out["watermark"]["id"]} if out["watermark"] else set())
    out["skipped"] = [{"id": k, "reason": v} for k, v in sorted(ctx.skipped.items()) if k not in used_ids]
    if mode == "auto" and ctx.shop and not items:
        ctx.notes.append("AUTO không chèn animation nào: " + ("; ".join(f"{s['id']}: {s['reason']}" for s in out["skipped"]
                                                                       if s["id"] in out["library"]["usable_ids"])
                                                             or "thư viện shop trống"))
    _save(job_dir, out)
    return out


def _save(job_dir: Path, plan_: dict) -> None:
    (job_dir / "motion_plan.json").write_text(json.dumps(plan_, ensure_ascii=False, indent=2, default=str),
                                             encoding="utf-8")


# ───────────────────────────── compositor (filter ffmpeg) ─────────────────────────────

def _geq_alpha(expr: str) -> str:
    return f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*{expr}'"


def chain_item(k: int, prev: str, out: str, it: dict) -> tuple[list[str], list[str]]:
    """(input, filter) chèn clip alpha `it` tại input số k: cắt vùng hiển thị + mờ mép cắt, phát tới `play_until` (mờ ra),
    co giãn về cỡ đặt, độ mờ, dời giờ bắt đầu."""
    f = ["format=rgba"]
    if it.get("play_until"):
        pu, fo = it["play_until"], max(0.05, it.get("fade_out") or 0.3)
        f += [f"trim=0:{pu:.3f}", f"fade=t=out:st={max(0.0, pu - fo):.3f}:d={fo:.3f}:alpha=1"]
    if it.get("crop"):
        cx, cy, cw, ch = it["crop"]
        f.append(f"crop={cw}:{ch}:{cx}:{cy}")
    fe = it.get("feather") or {}
    terms = [t for t in ((f"min(1,(X+0.5)/{fe['l']})" if fe.get("l") else ""),
                         (f"min(1,(W-X-0.5)/{fe['r']})" if fe.get("r") else ""),
                         (f"min(1,(Y+0.5)/{fe['t']})" if fe.get("t") else ""),
                         (f"min(1,(H-Y-0.5)/{fe['b']})" if fe.get("b") else "")) if t]
    if terms:
        f.append(_geq_alpha("*".join(terms)))
    f.append(f"scale={it['w']}:{it['h']}:flags=lanczos")
    if it["opacity"] < 0.999:
        f.append(f"colorchannelmixer=aa={it['opacity']:.3f}")
    f.append(f"setpts=PTS-STARTPTS+{it['start']:.3f}/TB")
    return ["-i", it["mov"]], [f"[{k}:v]{','.join(f)}[m{k}]",
                                f"[{prev}][m{k}]overlay=x={it['x']}:y={it['y']}:eof_action=pass:"
                                f"enable='between(t,{it['start']:.3f},{it['end']:.3f})'[{out}]"]


def logo_alpha(hidden: list[list[float]], fade_out: float = LOGO_FADE, fade_in: float = HANDOFF) -> str:
    """Biểu thức độ hiện logo theo thời gian T: 1 ngoài các khoảng ẩn; mờ ra trong `fade_out` trước khoảng ẩn, hiện lại
    trong `fade_in` sau khoảng ẩn. Khoảng ẩn bắt đầu ~0 → ẩn ngay từ khung đầu (không nháy)."""
    terms = []
    for a, b in hidden:
        fo = fade_out if a > 0.05 else 0.001
        terms.append(f"min(1,max(0,max(({a:.3f}-T)/{fo:.3f},(T-{b:.3f})/{fade_in:.3f})))")
    return "*".join(terms) or "1"


def chain_logo(k: int, prev: str, out: str, lp: dict, lg: dict, fps: float, main_dur: float) -> tuple[list[str], list[str]]:
    """Logo thường trực có khoảng ẩn: ảnh lặp suốt video chính, độ hiện theo `logo_alpha`."""
    ins = ["-loop", "1", "-framerate", f"{fps}", "-t", f"{main_dur:.3f}", "-i", str(lp["png"])]
    return ins, [f"[{k}:v]format=rgba,{_geq_alpha(logo_alpha(lg['hidden'], lg['fade_out'], lg['fade_in']))}[lg{k}]",
                 f"[{prev}][lg{k}]overlay={lp['x']}:{lp['y']}:eof_action=pass[{out}]"]


def _piecewise(segs: list[dict], key: str) -> str:
    """Toạ độ hằng theo chặng: if(t<bắt đầu chặng 2, chỗ 1, if(t<bắt đầu chặng 3, chỗ 2, …)) — đổi chỗ tức thì đúng lúc
    độ hiện = 0 (không trượt)."""
    expr = str(segs[-1][key])
    for i in range(len(segs) - 2, -1, -1):
        expr = f"if(lt(t,{segs[i + 1]['start']:.3f}),{segs[i][key]},{expr})"
    return expr


def _slide(segs: list[dict], key: str) -> str:
    """Toạ độ trượt êm (smoothstep, watermark.MOVE giây) sang chỗ mới ở đầu mỗi chặng — như watermark chữ trôi cũ."""
    expr = str(segs[0][key])
    for prev, s in zip(segs, segs[1:]):
        expr = f"if(lt(t,{s['start']:.3f}),{expr},{watermark._smooth(prev[key], s[key], s['start'])})"
    return expr


def chain_watermark(k: int, prev: str, out: str, wm: dict, main_dur: float) -> tuple[list[str], list[str]]:
    """Watermark động: phát INTRO tới khung giữ → giữ khung đó (tpad) → [chìm dần về opacity] → đổi chỗ: "slide" trượt êm
    sang chỗ mới (như cũ) · "fade" độ hiện về 0 đúng lúc chuyển chặng (mờ ra chỗ cũ, hiện ở chỗ mới) → mờ hẳn trước outro."""
    life, st, c = wm["life"], wm["start"], wm["clip"]
    slide = wm.get("phases", {}).get("relocate_mode", life.get("relocate_mode", "slide")) == "slide"
    hold = max(0.1, main_dur - st - c + 0.2)
    env = []  # thời gian T của luồng watermark (0 = lúc watermark vào)
    if wm["dim"] > 0:
        o, d = wm["opacity"], wm["dim"]
        env.append(f"if(lt(T,{c:.3f}),1,max({o:.3f},1-(T-{c:.3f})/{d:.3f}*(1-{o:.3f})))")
    if not slide:
        rf = float(life.get("fade", 0.4))
        for r in wm["relocations"]:
            env.append(f"min(1,abs(T-{r - st:.3f})/{rf:.3f})")
    ef = float(life.get("exit", 0.4))
    env.append(f"min(1,max(0,({main_dur - st:.3f}-T)/{ef:.3f}))")
    f = ["format=rgba", f"trim=0:{c:.3f}", f"scale={wm['w']}:{wm['h']}:flags=lanczos",
         f"tpad=stop_mode=clone:stop_duration={hold:.3f}", _geq_alpha("*".join(env)),
         f"setpts=PTS-STARTPTS+{st:.3f}/TB"]
    pos = _slide if slide else _piecewise
    x, y = pos(wm["segments"], "x"), pos(wm["segments"], "y")
    return ["-i", wm["mov"]], [f"[{k}:v]{','.join(f)}[w{k}]",
                                f"[{prev}][w{k}]overlay=x='{x}':y='{y}':eval=frame:eof_action=pass:"
                                f"enable='gte(t,{st:.3f})'[{out}]"]


# ───────────────────────────── QA (số đo, không AI) ─────────────────────────────

def qa(job_dir: Path, video: Path, expected_total: float) -> dict | None:
    """Kiểm phần animation của bản dựng: clip còn + alpha đạt; logo thường trực liên tục (chỉ ẩn trong khoảng animation
    thay logo); animation không thay logo không đè logo; watermark đúng vòng đời (không đổi chỗ trước khi giữ đủ, đổi chỗ
    có mờ); không 2 watermark; chồng chữ ≤ 4%; thời lượng + tiếng. None = job không dùng motion."""
    p = job_dir / "motion_plan.json"
    edl = json.loads((job_dir / "edl.json").read_text(encoding="utf-8"))
    if not p.exists() or "motion" not in edl:
        return None
    mp = json.loads(p.read_text(encoding="utf-8"))
    problems, info = [], []
    for it in mp.get("items", []) + ([mp["watermark"]] if mp.get("watermark") else []):
        inf = Path(it["mov"]).parent / "info.json"
        if not Path(it["mov"]).exists() or not inf.exists():
            problems.append(f"{it['id']}: thiếu clip alpha trong cache ({it['mov']}) — render lại")
            continue
        chk = json.loads(inf.read_text(encoding="utf-8"))["check"]
        if chk.get("fatal"):
            problems.append(f"{it['id']}: clip lỗi alpha — {'; '.join(chk['fatal'])}")
        info += [f"{it['id']}: {w}" for w in chk.get("warn", [])]
        if it.get("overlap", 0) > MAX_OVERLAP:
            problems.append(f"{it['id']}: chồng ô chữ {it['overlap']:.0%} (> {MAX_OVERLAP:.0%})")
    lj = job_dir / "layers.json"
    layers = json.loads(lj.read_text(encoding="utf-8")) if lj.exists() else {}
    lg = mp.get("logo") or {}
    if lg.get("enabled") and not layers.get("logo"):
        problems.append("logo thường trực KHÔNG có trong bản dựng dù kế hoạch bật")
    reps = [it for it in mp.get("items", []) if "logo" in it.get("replaces", [])]
    for a, b in layers.get("logo_hidden", []):
        if not any(it["start"] - 0.01 <= a and b <= it["end"] + 0.01 for it in reps):
            problems.append(f"logo ẩn {a}–{b}s ngoài khoảng animation thay logo")
    hid = sum(b - a for a, b in layers.get("logo_hidden", []))
    if layers.get("logo") and hid > sum(it["end"] - it["start"] for it in reps) + 0.05:
        problems.append(f"logo ẩn {hid:.2f}s > tổng thời lượng animation thay logo")
    if layers.get("logo_rect"):
        lr = layers["logo_rect"]
        for it in mp.get("items", []):
            if "logo" not in it.get("replaces", []) and _inter(lr, (it["x"], it["y"], it["w"], it["h"])) > 0:
                problems.append(f"{it['id']} đè logo thường trực (2 logo chồng nhau)")
    wm = mp.get("watermark")
    if wm:
        if layers.get("watermark") != f"motion:{wm['id']}":
            problems.append(f"watermark bản dựng = {layers.get('watermark')} (kế hoạch: động {wm['id']})")
        ph, segs = wm["phases"], wm["segments"]
        settled = ph.get("settled", ph["hold"][0])
        if segs[0]["start"] != wm["start"] or (len(segs) > 1 and segs[1]["start"] < settled - 0.01):
            problems.append("watermark đổi chỗ khi chưa xuất hiện → chìm dần xong")
        if ph.get("relocate_mode", "slide") == "fade":
            hold_min = float(wm["life"].get("hold", 10)) * 0.6
            for s in segs[1:]:
                if s["end"] - s["start"] < hold_min - 0.01:
                    problems.append(f"chặng watermark {s['start']}–{s['end']}s ngắn hơn {hold_min:.1f}s")
        if not wm["life"].get("relocate", True) and len(segs) > 1:
            problems.append("shop tắt đổi chỗ nhưng watermark vẫn đổi chỗ")
    if layers.get("motion") is not None and layers["motion"] != [it["id"] for it in mp.get("items", [])]:
        problems.append(f"animation bản dựng {layers['motion']} ≠ kế hoạch — render lại")
    pr = json.loads(media.run([config.FFPROBE, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                               "-print_format", "json", str(video)]).stdout)
    got = float(pr["format"]["duration"])
    if abs(got - expected_total) > 0.15:
        problems.append(f"thời lượng bản dựng {got:.2f}s ≠ {expected_total:.2f}s")
    if not any(s.get("codec_type") == "audio" for s in pr.get("streams", [])):
        problems.append("bản dựng mất tiếng")
    return {"ok": not problems, "problems": problems, "info": info, "items": [it["id"] for it in mp.get("items", [])],
            "watermark": (wm or {}).get("id"), "logo": lg}


# ───────────────────────────── storyboard soát mắt ─────────────────────────────

def milestones(mp: dict, total: float) -> list[tuple[str, float]]:
    """Các mốc soát: trước / giữa / cuối brand reveal, logo tiếp quản, giữa video, watermark mờ / giữ / đổi chỗ, accent,
    trước outro, trong outro."""
    dur = mp["duration"]
    out = []
    items = mp.get("items", [])
    reps = [it for it in items if it.get("role") == "brand_reveal"] or [it for it in items if "logo" in it.get("replaces", [])]
    if reps:
        r = reps[0]
        out += [("trước reveal", max(0.0, r["start"] - 0.3)), ("giữa reveal", (r["start"] + r["end"]) / 2),
                ("reveal kết thúc", max(r["start"], r["end"] - 0.1)), ("logo tiếp quản", min(dur - 0.1, r["end"] + 0.4))]
    for it in items:
        if not reps or it is not reps[0]:
            out.append((f"{it['role']} {it['id']}", (it["start"] + it["end"]) / 2))
    out.append(("giữa video", dur / 2))
    wm = mp.get("watermark")
    if wm:
        ph = wm["phases"]
        if ph.get("dim"):
            out.append(("watermark đang mờ", (ph["dim"][0] + ph["dim"][1]) / 2))
        else:
            out.append(("watermark intro", (ph["intro"][0] + ph["intro"][1]) / 2))
        out.append(("watermark đã chìm", min(dur - 0.2, ph["hold"][0] + 0.8)))
        after = watermark.MOVE + 0.5 if ph.get("relocate_mode", "slide") == "slide" else 1.0  # chụp khi đã tới chỗ mới
        for r in wm.get("relocations", [])[:2]:
            out.append(("watermark chỗ mới", min(dur - 0.2, r + after)))
    out += [("trước outro", max(0.0, dur - 0.3))]
    if total > dur + 0.5:
        out.append(("trong outro", min(total - 0.2, dur + 1.2)))
    return sorted(out, key=lambda x: x[1])


def storyboard(job_dir: Path, video: Path, out: Path, before: Path | None = None) -> Path:
    """Ảnh soát: hàng SAU (bản dựng hiện tại) [+ hàng TRƯỚC (bản cũ) cùng mốc giờ]; nhãn tiếng Việt."""
    mp = json.loads((job_dir / "motion_plan.json").read_text(encoding="utf-8"))
    total = float(json.loads(media.run([config.FFPROBE, "-v", "error", "-show_entries", "format=duration",
                                        "-print_format", "json", str(video)]).stdout)["format"]["duration"])
    marks = milestones(mp, total)
    tw = 240
    font = ImageFont.truetype(str(config.FONT_BOLD), 15)
    small = ImageFont.truetype(str(config.FONT_REGULAR), 13)

    def grab(v: Path, t: float) -> Image.Image:
        cap = cv2.VideoCapture(str(v))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        cap.release()
        if not ok:
            return Image.new("RGB", (tw, round(tw * 4 / 3)), "#333")
        im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        return im.resize((tw, round(im.height * tw / im.width)))

    rows = [("SAU", video)] + ([("TRƯỚC", before)] if before else [])
    th = grab(video, 0.1).height
    head = 44
    sheet = Image.new("RGB", (len(marks) * (tw + 6) + 70, len(rows) * (th + 6) + head + 6), "#1d1d1d")
    d = ImageDraw.Draw(sheet)
    for c, (label, t) in enumerate(marks):
        x = 70 + c * (tw + 6)
        d.text((x + 4, 4), label, font=font, fill="#ffd54a")
        d.text((x + 4, 24), f"{t:.2f}s", font=small, fill="#dddddd")
        for r, (name, v) in enumerate(rows):
            sheet.paste(grab(v, t), (x, head + r * (th + 6)))
    for r, (name, _) in enumerate(rows):
        d.text((8, head + r * (th + 6) + th // 2 - 8), name, font=font, fill="#ffffff")
    sheet.save(out, quality=88)
    return out
