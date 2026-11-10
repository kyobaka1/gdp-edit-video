"""Dựng video từ edl.json: vẽ ô chữ PNG (Pillow) rồi ghép bằng ffmpeg overlay theo khung giờ."""

import json
import math
import re
from pathlib import Path

from PIL import Image

from studio import config, logo, media, motion, motiondirector, motionlib, outro, watermark
from studio.overlay import grow_to_min_font, render_label
from studio.templates import TemplateRenderer, has_marks, strip_marks

SFX = config.ROOT / "assets" / "sfx"
# tiếng khẽ khi ô bật vào / khối nhấn bật (edl.audio.sfx, Kenney CC0 — assets/sfx/README.md); âm lượng tuyến tính
SFX_LAND = {"hook": ("impactSoft_medium_001.ogg", 0.32), "badge": ("impactSoft_medium_004.ogg", 0.26),
            "callout-left": ("impactSoft_medium_004.ogg", 0.22), "callout-right": ("impactSoft_medium_004.ogg", 0.22)}
SFX_PUNCH = ("click_003.ogg", 0.22)


class EdlError(ValueError):
    pass


def _srt_time(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def rotated_rect(w: int, h: int, angle: float) -> tuple[int, int]:
    """Từ ô bao ngang (w×h) của một dòng chữ nghiêng `angle` độ → kích thước khung xoay ôm dòng chữ.
    Giải W = a·cos + b·sin, H = a·sin + b·cos. Gần 45° (định thức ~0) thì không xoay được → trả nguyên."""
    t = math.radians(abs(angle))
    c, s = math.cos(t), math.sin(t)
    det = c * c - s * s
    if det < 0.35:  # > ~35° — giải không ổn định
        return w, h
    a = (w * c - h * s) / det
    b = (h * c - w * s) / det
    b = max(b, 0.12 * a, 24)  # đừng để khung quá mỏng vì sai số ô bao
    return max(24, round(a)), max(24, round(b))


def _render_fx(renderer, tpl: str, text: str, w: int, h: int, *, sub: str = "", reveal: bool = False,
               **kw) -> tuple[Image.Image, int, int, dict | None]:
    """renderer.render + (nếu hiện dần hoặc có `*nhấn*`) ảnh từng bước cho motion.schedule."""
    want = reveal and tpl not in motion.NO_REVEAL
    on = want or has_marks(text) or has_marks(sub)
    img, w, h = renderer.render(tpl, text, w, h, sub=sub, fx=on, **kw)
    if not on:
        return img, w, h, None
    units = renderer.units()
    fx = renderer.states(motion.reveal_steps(units) if want else [len(units)])
    fx["reveal"] = want
    return img, w, h, fx


def _draw_label(L: dict, renderer, W: int, H: int) -> tuple[Image.Image, int, int, dict | None]:
    """Vẽ một ô chữ (mẫu brand nếu có, không thì Pillow), xoay theo góc chữ gốc. Trả (ảnh, x, y, fx) để overlay;
    fx = ảnh từng bước chữ hiện dần / khối nhấn (None nếu không có)."""
    min_px = round(H * 0.03)  # chữ Việt ≥ 3% chiều cao khung cho dễ đọc trên điện thoại
    angle = L["angle"]
    w, h = rotated_rect(L["w"], L["h"], angle) if angle else (L["w"], L["h"])
    max_w = round(W * 0.92) if not angle else round(w * 1.25)
    if renderer is not None and L.get("template"):
        if L.get("zh") and not renderer.covers(L["template"]):
            raise EdlError(f"Ô che chữ Trung '{L['zh']}' dùng mẫu '{L['template']}' KHÔNG nền (covers:false) — "
                           f"mẫu này chỉ để chèn chữ mới; chọn mẫu có nền")
        img, w, h, fx = _render_fx(renderer, L["template"], L["text"] or " ", w, h, sub=L["sub"], reveal=L["reveal"],
                                   min_px=min_px, max_w=max(max_w, w), max_h=h * 3)
    else:
        st, fx = L["style"], None
        text = strip_marks(L["text"])
        _, _, w, h = grow_to_min_font(text, 0, 0, w, h, max(max_w, w), H, min_px)
        img = render_label(text or " ", w, h, bg=st.get("bg", "#FFFFFF"),
                           border=st.get("border", "#D7262E"), text_color=st.get("text", "#1A1A1A"))
    if angle:
        rot = lambda im: im.rotate(angle, expand=True, resample=Image.BICUBIC)  # noqa: E731
        img = rot(img)  # PIL: dương = ngược chiều kim đồng hồ
        if fx:
            fx["shots"] = [rot(s) for s in fx["shots"]]
            fx["punch"] = {j: rot(s) for j, s in fx["punch"].items()}
            fx["punch_full"] = rot(fx["punch_full"]) if fx["punch_full"] is not None else None
    cx, cy = L["x"] + L["w"] / 2, L["y"] + L["h"] / 2
    ox, oy = round(cx - img.width / 2), round(cy - img.height / 2)
    if not angle:  # ô ngang nới rộng thì giữ trong khung
        ox = max(0, min(W - img.width, ox))
        oy = max(0, min(H - img.height, oy))
    return img, ox, oy, fx


def measure_lufs(path: Path) -> float | None:
    out = media.subprocess.run([config.FFMPEG, "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", out[out.rfind("Summary:"):])
    return float(m.group(1)) if m else None


def measure_true_peak(path: Path) -> float | None:
    out = media.subprocess.run([config.FFMPEG, "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null",
                                "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", out[out.rfind("True peak:"):])
    return None if not m or m.group(1) == "-inf" else float(m.group(1))


def _normalize_loudness(path: Path, target: float, tolerance: float = 0.5) -> float | None:
    """Đưa ĐỘ TO CẢ BẢN về mục tiêu: đo ebur128 → bù dB tuyến tính + chặn đỉnh, chép nguyên hình (-c:v copy).
    Chỉ chuẩn hoá từng lớp (giọng/nhạc) thì cả bản lệch theo giọng + kịch bản (20/10: LTENG VN −16,4, HCM −15,4,
    GDP −14,9 cùng thông số); loudnorm 1 lượt cũng hụt (−15,9 / −15,1)."""
    now = measure_lufs(path)
    if now is None:
        return now
    if abs(now - target) <= tolerance:
        # đúng độ to rồi vẫn phải chặn đỉnh: tiếng hiệu ứng / nhạc cộng vào giọng có thể vượt 0 dBTP (07/11: +0,1 dBTP
        # ở bản −14,3 LUFS vì bước này bị bỏ qua) → chạy 1 lượt bù 0 dB + limiter khi đỉnh thật > −1,2
        tp = measure_true_peak(path)
        if tp is None or tp <= -1.2:
            return now
    tmp = path.with_name(path.stem + "_norm" + path.suffix)
    gain, limit = target - now, 0.75
    for _ in range(4):  # limiter ăn bớt độ to sau khi bù → đo lại, bù thêm; luôn tính từ bản gốc (không mã hoá chồng)
        media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(path), "-c:v", "copy",
                   # chặn đỉnh 0,75 (~−2,5 dBFS), level=0: mặc định alimiter tự kéo âm lượng lại sát 0 dBFS
                   # (20/10 ra đỉnh +0,9 dBFS) ; AAC còn sinh thêm đỉnh ảo nên phải chừa khoảng
                   "-af", f"volume={gain:.2f}dB,alimiter=limit={limit:.3f}:level=0", "-c:a", "aac", "-b:a", "192k",
                   "-ar", "48000", "-movflags", "+faststart", str(tmp)])
        got, tp = measure_lufs(tmp), measure_true_peak(tmp)
        # tiếng rè / click gắt trong giọng gốc (07/11 test vlog: mẫu nhảy dấu ±0,3 ở 22,77s) → AAC sinh đỉnh GIỮA các mẫu
        # cao hơn ngưỡng chặn ~2,5 dB → hạ ngưỡng đúng phần vượt rồi mã hoá lại
        tp_bad = tp is not None and tp > -1.2
        if tp_bad:
            limit = max(0.4, limit * 10 ** ((-1.4 - tp) / 20))
        if (got is None or abs(got - target) <= tolerance) and not tp_bad:
            break
        if got is not None and abs(got - target) > tolerance:
            gain += target - got
    tmp.replace(path)
    return measure_lufs(path)


def _point_drift(video: Path, t0: float, t1: float, cx: int, cy: int) -> float:
    """Điểm (cx,cy) bị CAMERA dời bao nhiêu px giữa 2 mốc: khớp đặc trưng ORB → ước lượng dịch/xoay/phóng của cả khung.
    (Bản đầu đo chênh điểm ảnh tại chỗ → báo nhầm khi máy đứng yên nhưng đồ được thêm dần lên kệ.)"""
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(str(video))
    grays = []
    for t in (t0, t1):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            return 0.0
        grays.append(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
    cap.release()
    orb = cv2.ORB_create(1500)
    k1, d1 = orb.detectAndCompute(grays[0], None)
    k2, d2 = orb.detectAndCompute(grays[1], None)
    if d1 is None or d2 is None or len(k1) < 12 or len(k2) < 12:
        return 999.0  # không khớp được (cắt cảnh/đổi cảnh) → coi như lệch
    matches = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2), key=lambda m: m.distance)[:300]
    if len(matches) < 12:
        return 999.0
    src = np.float32([k1[m.queryIdx].pt for m in matches])
    dst = np.float32([k2[m.trainIdx].pt for m in matches])
    A, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0)
    if A is None or inl is None or inl.sum() < 10:
        return 999.0
    moved = A @ np.array([cx, cy, 1.0])
    return float(np.hypot(moved[0] - cx, moved[1] - cy))


def _draw_extra(e: dict, renderer, meta: dict, job_dir: Path, reveal: bool = False) -> dict:
    """Phần tử CHÈN MỚI (không che chữ Trung): lower third, callout chỉ vào sản phẩm."""
    W, H = meta["width"], meta["height"]
    tpl = e["template"]
    min_px = round(H * 0.026)
    reveal = e["reveal"] if e.get("reveal") is not None else reveal
    if tpl == "lower-third":
        w, h = round(W * e.get("w_pct", 0.64)), round(H * 0.085)
        img, w, h, fx = _render_fx(renderer, tpl, e["text"], w, h, sub=e.get("sub", ""), reveal=reveal,
                                   min_px=min_px, max_w=round(W * 0.9))
        x = round(W * 0.04)
        y = round(H * {"lower-left": 0.66, "upper-left": 0.14}.get(e.get("position", "lower-left"), 0.66))
    elif tpl in ("callout-left", "callout-right"):
        tx, ty = (int(v) for v in e["target"])  # điểm trên sản phẩm (pixel khung gốc) mà chấm tròn chỉ vào
        w, h = round(W * e.get("w_pct", 0.5)), round(H * 0.07)
        img, w, h, fx = _render_fx(renderer, tpl, e["text"], w, h, reveal=reveal, min_px=min_px, max_w=round(W * 0.7))
        dot = round(img.height * 0.17)  # tâm chấm nằm sát mép (mẫu: chấm = 0,34×h)
        x = tx - img.width + dot if tpl == "callout-left" else tx - dot
        y = ty - img.height // 2
        drift = _point_drift(job_dir / meta["source"], e["start"], e["end"], tx, ty)
        e["_drift"] = round(drift, 1)
        if drift > max(12, W * 0.02):
            print(f"  ⚠ callout '{e['text']}' {e['start']}–{e['end']}s: máy quay làm điểm chỉ dời {drift:.0f}px — "
                  f"chọn cảnh tĩnh hơn hoặc rút ngắn khung giờ")
        if x < 0 or y < 0 or x + img.width > W or y + img.height > H:
            print(f"  ⚠ callout '{e['text']}' tràn ra ngoài khung — đổi phía (callout-left/right) hoặc rút chữ")
    else:
        raise EdlError(f"extras: mẫu '{tpl}' không hỗ trợ (lower-third | callout-left | callout-right)")
    return {"img": img, "x": x, "y": y, "w": img.width, "h": img.height, "start": e["start"], "end": e["end"],
            "anim": e.get("anim") or motion.DEFAULT_ANIM.get(tpl, "fade"), "template": tpl, "fx": fx,
            "text": f"{e['text']} {e.get('sub', '')}".strip()}


def validate(edl: dict, meta: dict, allow_empty: bool) -> list[dict]:
    """Trả danh sách lớp phủ cần vẽ (ô chữ + phụ đề), mỗi lớp {start,end,x,y,w,h,text,style}."""
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    style = edl.get("style", {})
    layers, problems = [], []
    for o in edl.get("overlays", []):
        if o.get("skip") or o.get("mode") == "keep":  # keep = chữ trong cảnh, giữ nguyên
            continue
        x, y, w, h = (int(v) for v in o["box"])
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"{o['id']}: ô {o['box']} ra ngoài khung {W}x{H}")
        if not (0 <= o["start"] < o["end"] <= dur + 0.05):
            problems.append(f"{o['id']}: khung giờ {o['start']}–{o['end']} sai (video {dur}s)")
        mode = o.get("mode", "label")
        text = (o.get("text_vi") or "").strip()
        if mode == "label" and not text and not allow_empty:
            problems.append(f"{o['id']}: chưa có text_vi (chữ gốc: {o.get('zh')}) — hoặc đặt mode=blur / skip")
        if mode not in ("label", "blur"):
            problems.append(f"{o['id']}: mode '{mode}' không hỗ trợ (label | blur | keep)")
        layers.append({"start": o["start"], "end": o["end"], "x": x, "y": y, "w": w, "h": h,
                       "text": text, "sub": (o.get("sub_vi") or "").strip(), "mode": mode, "zh": o.get("zh", ""),
                       "angle": float(o.get("angle") or 0.0), "template": o.get("template"), "anim": o.get("anim"),
                       "reveal": o.get("reveal"), "style": {**style, **o.get("style", {})}})
    sb = edl.get("subtitle_box", {"y_pct": 0.78, "h_pct": 0.075, "w_pct": 0.9})
    sw, sh = round(W * sb["w_pct"]), round(H * sb["h_pct"])
    sx, sy = (W - sw) // 2, round(H * sb["y_pct"])
    for i, s in enumerate(edl.get("subtitles", []), 1):
        text = (s.get("text_vi") or "").strip()
        if s.get("skip") or not text:
            continue
        if not (0 <= s["start"] < s["end"] <= dur + 0.05):
            problems.append(f"phụ đề {i}: khung giờ {s['start']}–{s['end']} sai")
        layers.append({"start": s["start"], "end": s["end"], "x": sx, "y": sy, "w": sw, "h": sh,
                       "text": text, "sub": "", "mode": "label", "angle": 0.0, "template": "caption",
                       "reveal": s.get("reveal"), "style": {**style, **edl.get("subtitle_style", {})}})
    if problems:
        raise EdlError("edl.json chưa hợp lệ:\n  - " + "\n  - ".join(problems))
    return layers


def _poster(job_dir: Path, edl: dict, meta: dict, items: list[dict], inputs: list[str], chain: list[str],
            final: bool) -> dict | None:
    """Ảnh bìa (học từ brag): khung ĐÃ GHÉP ở lúc chữ đứng yên của ô mạnh nhất (hook > badge > ô đầu tiên),
    ghi <final|preview>.jpg + PNG để gắn làm khung 0 — Shopee/TikTok/Zalo lấy khung 0 làm ảnh chờ.
    Job khai `edl.poster = {"mode": "auto"}` hoặc `{"at": giây}` (chọn tay); không khai = flow cũ (khung 0 gốc).
    Dùng đúng đồ thị lọc hình nên khớp từng điểm ảnh."""
    cfg = edl.get("poster")
    cfg = cfg if isinstance(cfg, dict) else {}
    dur = meta["duration"]
    if "at" in cfg:
        at, why = float(cfg["at"]), "edl.poster.at"
    else:
        settled = lambda it: round(max(it["start"], it["full_at"]) + 0.3, 3)  # noqa: E731
        ok = sorted((it for it in items if it["text"] and settled(it) < min(it["end"] - 0.05, dur)),
                    key=lambda it: it["start"])
        rank = {"hook": 0, "badge": 1}
        pick = min(ok, key=lambda it: rank.get(it.get("template"), 2), default=None)
        at, why = (settled(pick), f"ô {pick.get('template') or 'chữ'} '{pick['text'][:40]}' đủ chữ") if pick else \
            (min(1.5, dur * 0.2), "không có ô chữ đứng đủ lâu — lấy 1,5s")
    png = job_dir / ("poster_final.png" if final else "poster_preview.png")
    filt = job_dir / "poster_filter.txt"
    filt.write_text(";\n".join(chain), encoding="utf-8")
    media.run([config.FFMPEG, "-y", "-v", "error", *inputs, "-/filter_complex", str(filt), "-map", "[vfin]",
               "-ss", f"{at:.3f}", "-frames:v", "1", str(png)])
    Image.open(png).convert("RGB").save(job_dir / ("final.jpg" if final else "preview.jpg"), quality=92)
    return {"png": png, "at": at, "why": why}


def _sfx_events(items: list[dict]) -> list[tuple[str, float, float]]:
    """(file, âm lượng, giây) — tiếng khẽ khi hook/badge/callout bật vào + khi khối nhấn bật. Thưa, ≥0,3s cách nhau,
    tối đa 16 tiếng / video (brag: hiệu ứng nằm dưới nhạc, lặp lại thì phải khẽ)."""
    ev = []
    for it in items:
        land = SFX_LAND.get(it.get("template"))
        if land:
            ev.append((*land, it["s0"] + (motion.LEAD * 0.8 if it["anim_in"] != "none" else 0.0)))
        ev += [(*SFX_PUNCH, t) for t in it.get("punch_at", [])]
    out, last = [], -1.0
    for e in sorted(ev, key=lambda e: e[2]):
        if e[2] - last >= 0.3 and len(out) < 16:
            out.append(e)
            last = e[2]
    return out


def label_boxes(job_dir: Path, edl: dict, meta: dict) -> list[dict]:
    """Vùng chữ ƯỚC LƯỢNG (ô gốc, chưa nới theo mẫu) + chữ trong cảnh — cho `vs.py motion plan` xem trước, không vẽ ô.
    Lúc render thật, motiondirector nhận vùng chữ đã vẽ (chính xác hơn)."""
    out = [{"x": L["x"], "y": L["y"], "w": L["w"], "h": L["h"], "start": max(0.0, L["start"] - motion.LEAD),
            "end": L["end"] + motion.FADE_OUT} for L in validate(edl, meta, allow_empty=True) if L["mode"] == "label"]
    W, H = meta["width"], meta["height"]
    for e in edl.get("extras", []):
        if e.get("skip"):
            continue
        if e.get("template") == "lower-third":
            w, h = round(W * e.get("w_pct", 0.64)), round(H * 0.085)
            y = round(H * {"lower-left": 0.66, "upper-left": 0.14}.get(e.get("position", "lower-left"), 0.66))
            out.append({"x": round(W * 0.04), "y": y, "w": w, "h": h, "start": e["start"], "end": e["end"]})
        elif "target" in e:
            tx, ty = (int(v) for v in e["target"])
            w, h = round(W * e.get("w_pct", 0.5)), round(H * 0.07)
            x = tx - w if e["template"] == "callout-left" else tx
            out.append({"x": x, "y": ty - h // 2, "w": w, "h": h, "start": e["start"], "end": e["end"]})
    out += [{"x": o["box"][0], "y": o["box"][1], "w": o["box"][2], "h": o["box"][3], "start": o["start"], "end": o["end"]}
            for o in edl.get("overlays", []) if o.get("mode") == "keep"]
    return out


def run(job_dir: Path, final: bool = False, allow_empty: bool = False) -> Path:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    edl_path = job_dir / "edl.json"
    if not edl_path.exists():
        raise EdlError("Chưa có edl.json (copy từ edl.draft.json rồi điền text_vi)")
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    layers = validate(edl, meta, allow_empty)

    labels_dir = job_dir / "labels"
    labels_dir.mkdir(exist_ok=True)
    for old in [*labels_dir.glob("*.png"), *labels_dir.glob("*.ffconcat")]:
        old.unlink()
    # chữ hiện dần (Sếp 29/10): job khai edl.reveal = {"mode": "auto"}; job cũ không khai = chữ ra cả câu như cũ.
    # `*nhấn*` trong chữ thì luôn có khối nhấn. Từng ô ép bằng "reveal": true/false.
    rv = edl.get("reveal")
    reveal_on = bool(rv) and not (rv == "off" or (isinstance(rv, dict) and rv.get("mode") == "off"))
    W, H = meta["width"], meta["height"]
    shop = edl.get("shop") or ""
    extras = [e for e in edl.get("extras", []) if not e.get("skip")]
    needs = any(L.get("template") for L in layers if L["mode"] == "label") or bool(extras)
    if needs and not shop:
        raise EdlError("edl.json có ô dùng `template`/extras nhưng chưa khai `shop` (mã shop trong assets/shops/)")
    op = outro.plan(edl)  # video outro Sếp đưa sẵn của shop — None nếu job không bật
    total = round(meta["duration"] + (op["duration"] if op else 0.0), 3)
    renderer = TemplateRenderer(shop).__enter__() if needs else None
    try:
        for L in layers:
            L["reveal"] = reveal_on if L.get("reveal") is None else bool(L["reveal"])
        drawn = {id(L): _draw_label(L, renderer, W, H) for L in layers if L["mode"] == "label"}
        extra_items = [_draw_extra(e, renderer, meta, job_dir, reveal_on) for e in extras]
    finally:
        if renderer is not None:
            renderer.__exit__(None, None, None)

    inputs = ["-i", str(job_dir / meta["source"])]
    chain, prev, n_png = [], "0:v", 0
    # 1) làm mờ (dưới cùng)
    for i, L in enumerate([L for L in layers if L["mode"] == "blur"], 1):
        out = f"vb{i}"
        enable = f"enable='between(t,{L['start']:.3f},{L['end']:.3f})'"
        # bán kính ≤ nửa cạnh ngắn; kênh màu yuv420 chỉ bằng nửa kích thước → bán kính màu chia đôi
        bw, bh = L["w"] // 2 * 2, L["h"] // 2 * 2
        r = max(2, min(bw, bh) // 5)
        chain.append(f"[{prev}]split[s{i}a][s{i}b]")
        chain.append(f"[s{i}b]crop={bw}:{bh}:{L['x']}:{L['y']},"
                     f"boxblur=luma_radius={r}:luma_power=3:chroma_radius={max(1, r // 2)}:chroma_power=3[b{i}]")
        chain.append(f"[s{i}a][b{i}]overlay={L['x']}:{L['y']}:{enable}[{out}]")
        prev = out

    # 2) ô chữ + phần tử chèn (lower third, callout) — có hiệu ứng vào/ra theo motion.py (giữ che phủ chữ Trung)
    def save_fx(fx: dict | None, png: Path) -> dict | None:
        if not fx:
            return None
        shots = []
        for j, im in enumerate(fx["shots"]):
            shots.append(png.with_name(f"{png.stem}_s{j}.png"))
            im.save(shots[-1])
        punch = {}
        for j, im in fx["punch"].items():
            punch[j] = png.with_name(f"{png.stem}_p{j}.png")
            im.save(punch[j])
        full = None
        if fx.get("punch_full") is not None:
            full = png.with_name(f"{png.stem}_pf.png")
            fx["punch_full"].save(full)
        return {"shots": shots, "punch": punch, "punch_full": full, "reveal": fx["reveal"]}

    items = []
    for L in layers:
        if L["mode"] != "label":
            continue
        img, ox, oy, fx = drawn[id(L)]
        n = len(items) + 1
        png = labels_dir / f"l{n:03}.png"
        img.save(png)
        items.append({"png": png, "x": ox, "y": oy, "w": img.width, "h": img.height, "start": L["start"],
                      "end": L["end"], "covers": bool(L.get("zh")), "template": L.get("template") or "",
                      "text": strip_marks(f"{L['text']} {L['sub']}").strip(), "fx": save_fx(fx, png),
                      "anim": L.get("anim") or motion.DEFAULT_ANIM.get(L.get("template") or "", "fade")})
    for e in extra_items:
        n = len(items) + 1
        png = labels_dir / f"l{n:03}.png"
        e.pop("img").save(png)
        items.append({**e, "png": png, "covers": False, "fx": save_fx(e["fx"], png), "text": strip_marks(e["text"])})
    motion.plan_layers(items)
    for it in items:
        it["floor"] = motion.read_floor(it["text"])
        motion.schedule(it)
    # Chữ hiện không kịp đọc (học từ brag: ~0,25s/âm tiết, tối thiểu 0,8s, tính từ lúc đủ chữ) → chỉ CẢNH BÁO:
    # mốc ô che chữ Trung theo video gốc, cách sửa là rút bản dịch / gộp ô, không kéo dài ô.
    read_warn = []
    for it in items:
        shown = it["end"] - max(it["start"], it["full_at"])
        if it["text"] and shown < it["floor"] - 0.05:
            read_warn.append(f"'{it['text']}' {it['start']:.2f}–{it['end']:.2f}s: đọc được {max(0, shown):.2f}s, "
                             f"cần ~{it['floor']:.1f}s → rút chữ / gộp ô")
    for w in read_warn:
        print(f"  ⚠ chữ hiện ngắn: {w}")
    boxes = [{"x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"], "start": it["s0"], "end": it["e1"]} for it in items]
    boxes += [{"x": o["box"][0], "y": o["box"][1], "w": o["box"][2], "h": o["box"][3], "start": o["start"], "end": o["end"]}
              for o in edl.get("overlays", []) if o.get("mode") == "keep"]

    # Nhận diện động (chỉ khi edl.motion có khai — không khai = flow cũ y nguyên, kể cả cỡ logo + watermark chữ trôi):
    # logo THƯỜNG TRỰC V2 (nhỏ, sát mép trên, chỉ tạm ẩn trong KHOẢNG animation thay logo), animation từ thư viện
    # assets/motion, watermark động V2 thay chữ. Tất cả ghép TRƯỚC khi nối outro → không đè outro.
    mcfg = edl.get("motion")
    motion_on = "motion" in edl and not (mcfg is False or mcfg == "off" or (isinstance(mcfg, dict) and mcfg.get("mode") == "off"))
    lp = logo.plan(job_dir, edl, meta, boxes, persistent=motion_on)
    try:
        mp = motiondirector.plan(job_dir, edl, meta, boxes, (lp["x"], lp["y"], lp["w"], lp["h"]) if lp else None)
    except (motiondirector.MotionPlanError, motionlib.MotionError) as exc:
        raise EdlError(f"Animation: {exc}")
    m_items = mp["items"] if mp else []
    m_logo = mp["logo"] if mp else None
    m_wm = mp["watermark"] if mp else None
    wp = None
    if m_wm:  # watermark động V2: intro → dim → giữ 1 chỗ → đổi chỗ có điều kiện → mờ trước outro
        n_png += 1
        ins, lines = motiondirector.chain_watermark(n_png, prev, "vwm", m_wm, meta["duration"])
        inputs += ins
        chain += lines
        prev = "vwm"
    else:  # watermark chữ trôi (dưới ô chữ, trên hình) — chống lấy cắp; né ô chữ + góc logo; không có trên outro
        wboxes = boxes + [{"x": it["x"], "y": it["y"], "w": it["w"], "h": it["h"], "start": it["start"],
                           "end": it["end"]} for it in m_items]
        wp = watermark.plan(job_dir, edl, meta, wboxes, (lp["x"], lp["y"], lp["w"], lp["h"]) if lp else None)
        if wp:
            n_png += 1
            inputs += ["-i", str(wp["png"])]
            chain.append(f"[{prev}][{n_png}:v]overlay=x='{wp['x']}':y='{wp['y']}':eval=frame[vwm]")
            prev = "vwm"
    for it in [m for m in m_items if m["z"] != "top"]:  # animation nằm DƯỚI ô chữ (mặc định): chữ luôn đọc được
        n_png += 1
        ins, lines = motiondirector.chain_item(n_png, prev, f"vm{n_png}", it)
        inputs += ins
        chain += lines
        prev = f"vm{n_png}"
    for j, it in enumerate(items, 1):
        n_png += 1
        ins, lines = motion.chain(n_png, prev, f"v{j}", it, meta["fps"])
        inputs += ins
        chain += lines
        prev = f"v{j}"
    # Logo chính của shop: suốt phần video chính, vẽ trên cùng; góc do logo.plan tự chọn (né ô chữ + chỗ nhiều chi tiết).
    # Gắn TRƯỚC khi nối outro → outro không có logo đè.
    if lp:
        n_png += 1
        if m_logo and m_logo["hidden"]:  # logo thường trực chỉ ẩn trong khoảng animation thay logo (có chuyển giao)
            ins, lines = motiondirector.chain_logo(n_png, prev, "vlogo", lp, m_logo, meta["fps"], meta["duration"])
            inputs += ins
            chain += lines
        else:
            inputs += ["-i", str(lp["png"])]
            chain.append(f"[{prev}][{n_png}:v]overlay={lp['x']}:{lp['y']}[vlogo]")
        prev = "vlogo"
    for it in [m for m in m_items if m["z"] == "top"]:  # animation khai z=top: trên cả chữ + logo
        n_png += 1
        ins, lines = motiondirector.chain_item(n_png, prev, f"vm{n_png}", it)
        inputs += ins
        chain += lines
        prev = f"vm{n_png}"

    scale = ",scale=-2:960" if not final else ""
    pc = edl.get("poster")  # ảnh bìa = khung 0: job khai mới có (job cũ: filter + khung y nguyên như trước)
    poster_on = bool(pc) and pc != "off" and not (isinstance(pc, dict) and pc.get("mode") == "off")
    vl = "vfin" if poster_on else "vout"
    n_in = n_png + 1
    if op:
        # nối video outro của shop sau video chính: đưa về cùng kích thước (giữ tỉ lệ, viền đen nếu lệch)/fps rồi concat.
        # Tiếng của outro (nếu có) chưa trộn — outro GDP hiện không có tiếng; nhạc nền + câu chốt chạy tiếp qua outro.
        inputs += ["-i", str(op["path"])]
        chain.append(f"[{n_in}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                     f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={meta['fps']},format=yuv420p,setsar=1[ov]")
        chain.append(f"[{prev}]format=yuv420p,setsar=1[vm]")
        chain.append(f"[vm][ov]concat=n=2:v=1:a=0,format=yuv420p{scale}[{vl}]")
        n_in += 1
    else:
        chain.append(f"[{prev}]format=yuv420p{scale}[{vl}]")
    poster = _poster(job_dir, edl, meta, items, inputs, chain, final) if poster_on else None

    audio = edl.get("audio", {})
    mode = audio.get("mode", "keep")
    a_args: list[str]
    events: list = []
    if mode == "keep" and meta["has_audio"]:
        if op:  # tiếng gốc ngắn hơn bản có outro → đệm im lặng
            chain.append(f"[0:a]apad,atrim=0:{total:.3f}[aout]")
            a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
        else:
            a_args = ["-map", "0:a:0", "-c:a", "aac", "-b:a", "160k"]
    elif mode == "narration":
        # Thuyết minh liền mạch (narration.wav, 1 lượt đọc) + nhạc nền chuẩn hoá theo độ to cảm nhận (LUFS).
        # Bản 20/10 trước dùng sidechain ducking → nhạc bị nén gần như mất, Sếp nghe "chưa có nhạc".
        npath = job_dir / "narration.json"
        if not npath.exists():
            raise EdlError("audio.mode=narration nhưng chưa có narration.json — chạy `vs.py narrate <id>` trước")
        nrep = json.loads(npath.read_text(encoding="utf-8"))
        if any("tràn" in w for w in nrep.get("warnings", [])):
            raise EdlError("Thuyết minh tràn quá cuối video:\n  - " + "\n  - ".join(nrep["warnings"]))
        dur = total  # gồm cả outro
        voice_lufs = audio.get("voice_lufs", -16)
        music_lufs = audio.get("music_lufs", -27)
        inputs += ["-i", str(job_dir / "narration.wav")]
        chain.append(f"[{n_in}:a]aresample=48000,loudnorm=I={voice_lufs}:TP=-2:LRA=11,apad,atrim=0:{dur:.3f}[vo]")
        events = _sfx_events(items) if audio.get("sfx") else []
        mx = "mix0" if events else "mix"  # không sfx → chuỗi lọc y như trước
        music = Path(audio.get("music") or job_dir / "music.mp3")
        if not music.is_absolute():
            music = job_dir / music
        if music.exists():
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            chain.append(f"[{n_in + 1}:a]atrim=0:{dur:.3f},aresample=48000,loudnorm=I={music_lufs}:TP=-8:LRA=11,"
                         f"afade=t=in:d=0.4,afade=t=out:st={max(0.0, dur - 1.8):.3f}:d=1.8[bg]")
            chain.append(f"[vo][bg]amix=inputs=2:normalize=0:duration=first[{mx}]")
        else:
            chain.append(f"[vo]anull[{mx}]")
        k = n_in + (2 if music.exists() else 1)
        for j, (f, vol, t) in enumerate(events):
            ms = round(t * 1000)
            inputs += ["-i", str(SFX / f)]
            chain.append(f"[{k + j}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol},"
                         f"adelay={ms}|{ms}[sfx{j}]")
        if events:  # tiếng khẽ dưới nhạc + giọng; độ to cả bản vẫn bù về −14 sau khi render
            chain.append(f"[mix0]{''.join(f'[sfx{j}]' for j in range(len(events)))}"
                         f"amix=inputs={len(events) + 1}:normalize=0:duration=first[mix]")
        # độ to CẢ BẢN được bù sau khi render (_normalize_loudness) — đo thật rồi bù dB, chắc hơn loudnorm 1 lượt
        chain.append("[mix]alimiter=limit=0.95:level=0,aresample=48000[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    elif mode == "voice":
        # giọng Việt (voice.json, đã qua kiểm ngược) + nhạc nền tự hạ khi có giọng, mờ dần cuối video
        vpath = job_dir / "voice.json"
        if not vpath.exists():
            raise EdlError("audio.mode=voice nhưng chưa có voice.json — chạy `vs.py voice <id>` trước")
        vrep = json.loads(vpath.read_text(encoding="utf-8"))
        if vrep.get("too_long"):
            raise EdlError("Có câu đọc quá dài so với khung:\n  - " + "\n  - ".join(vrep["too_long"]))
        dur = total  # gồm cả outro
        k = n_in
        vo_labels = []
        for j, ln in enumerate(vrep["lines"]):
            inputs += ["-i", str(job_dir / "voice" / ln["file"])]
            ms = round(ln["start"] * 1000)
            tempo = f"atempo={ln['tempo']}," if ln["tempo"] > 1.0 else ""
            chain.append(f"[{k}:a]{tempo}adelay={ms}|{ms}[vo{j}]")
            vo_labels.append(f"[vo{j}]")
            k += 1
        chain.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0,apad[vomix]")
        music = Path(audio.get("music") or job_dir / "music.mp3")
        if not music.is_absolute():
            music = job_dir / music
        if music.exists():
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            chain.append(f"[{k}:a]atrim=0:{dur:.3f},volume={audio.get('music_volume', 0.25)},"
                         f"afade=t=out:st={max(0.0, dur - 1.5):.3f}:d=1.5[bg]")
            chain.append("[vomix]asplit[vo_a][vo_b]")
            chain.append("[bg][vo_a]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=350[bgd]")
            chain.append("[bgd][vo_b]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95:level=0[aout]")
        else:
            chain.append(f"[vomix]atrim=0:{dur:.3f},alimiter=limit=0.95:level=0[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    elif mode == "music":
        music = Path(audio.get("music") or "")
        if not music.is_absolute():
            music = config.ROOT / music
        if not music.exists():
            raise EdlError(f"audio.mode=music nhưng không thấy file nhạc: {music}")
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        chain.append(f"[{n_in}:a]volume={audio.get('music_volume', 0.25)}[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    else:  # mute: track im lặng để sàn không từ chối video thiếu audio
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        a_args = ["-map", f"{n_in}:a", "-c:a", "aac", "-b:a", "96k"]

    if poster:  # ảnh bìa = khung 0 (thay đúng 1 khung, không thêm khung → độ dài + tiếng giữ nguyên)
        inputs += ["-i", str(poster["png"])]
        chain.append(f"[vfin][{inputs.count('-i') - 1}:v]overlay=0:0:enable='eq(n,0)'[vout]")

    out_path = job_dir / ("final.mp4" if final else "preview.mp4")
    # các lớp THẬT đã ghép (QA + test đọc file này — filter.txt không có tên file input)
    (job_dir / "layers.json").write_text(json.dumps({
        "logo": bool(lp), "logo_rect": [lp["x"], lp["y"], lp["w"], lp["h"]] if lp else None,
        "logo_mode": ("persistent" if motion_on else "legacy") if lp else None,
        "logo_hidden": (m_logo or {}).get("hidden", []) if lp else [],
        "watermark": f"motion:{m_wm['id']}" if m_wm else ("text" if wp else None),
        "watermark_segments": m_wm["segments"] if m_wm else None,
        "motion": [it["id"] for it in m_items], "labels": len(items), "outro": bool(op), "final": final,
        "reveal": sum(1 for it in items if it.get("revealed")),
        "highlights": sum(len(it["punch_at"]) for it in items), "read_warnings": read_warn,
        "poster": {"at": poster["at"], "why": poster["why"]} if poster else None,
        "sfx": len(events) if mode == "narration" else 0},
        ensure_ascii=False, indent=2), encoding="utf-8")
    filter_file = job_dir / "filter.txt"
    filter_file.write_text(";\n".join(chain), encoding="utf-8")
    v_args = ["-c:v", "libx264", "-preset", "medium" if final else "veryfast", "-crf", "18" if final else "26"]
    media.run([config.FFMPEG, "-y", "-v", "error", *inputs, "-/filter_complex", str(filter_file),
               "-map", "[vout]", *v_args, *a_args, "-t", f"{total:.3f}",
               "-movflags", "+faststart", str(out_path)])

    if mode in ("narration", "voice", "music"):  # tiếng do studio trộn → bù độ to cả bản về mục tiêu (mặc định −14)
        _normalize_loudness(out_path, float(audio.get("target_lufs", -14)))

    subs = [s for s in edl.get("subtitles", []) if (s.get("text_vi") or "").strip() and not s.get("skip")]
    if subs:
        srt = "\n".join(f"{i}\n{_srt_time(s['start'])} --> {_srt_time(s['end'])}\n{strip_marks(s['text_vi']).strip()}\n"
                        for i, s in enumerate(subs, 1))
        out_path.with_suffix(".srt").write_text(srt, encoding="utf-8")
    return out_path
