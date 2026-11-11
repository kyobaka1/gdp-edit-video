"""CHỮ VIỆT ĐỘNG cho Việt hoá V2 (Sếp 11/11) — dùng lại bộ chữ động + Phong cách (Style Pack) của skill gdp-video-edit
(`assets/kinetic/`, `assets/styles/`, `studio/edit/kinetic.py`): nhiều độ đậm trong một khối (dòng thường / cụm khoá đậm /
dòng phụ mảnh / hộp nhấn màu shop), từng từ mờ-trồi vào mượt, rút ra êm.

Khác ô mẫu shop (`overlays[].template`): chữ Việt ở đây KHÔNG gánh việc che chữ Trung (việc đó của `studio/clean.py`) nên
không bị buộc theo mốc chữ Trung, đặt tự do theo khung hình. Ba chỗ đặt (Sếp chốt 11/11):
- chữ Trung ở ĐÁY / ĐỈNH → clean.py đã phủ KHUNG DẢI (chỉ trong lúc có chữ Trung); khối chữ không ghi `y` tự nằm giữa
  khung dải đáy (`"band": "top"` = khung dải đỉnh). Trên khung không cần bóng; khối rơi vào lúc khung KHÔNG hiện thì
  vẫn đứng đúng chỗ đó nhưng có bóng mềm (chữ trên hình) + cảnh báo.
- chữ Trung ở GIỮA khung → `"over": "<id ô>"`: khối chữ nằm trên BADGE nền đục che kín đúng vùng đã xoá (xoay cùng
  góc, hiện suốt thời gian chữ Trung có mặt), chữ tự phóng vừa badge. Không để lộ mảng nhoè.
- chữ CHÈN MỚI trên hình (không có chữ Trung bên dưới) → `x`, `y` tự do, có bóng tối mềm sau chữ (`scrim`).

    edl["caps"] = {
      "style": "phaledo-tap-chi",            # không ghi = theo brand (PHALEDO → phaledo-tap-chi, khác → san-pham-thuan)
      "scrim": "auto",                       # bóng sau khối chữ đặt trên hình (0 = tắt, 0–0.5 ép tay)
      "plate": {"bg": "#161616", "alpha": 0.93, "line": "#b89a6a"},   # badge (không ghi = theo màu shop)
      "items": [
        {"over": "o2", "text": "!Bếp bừa bộn?"},                              # badge lấp chữ Trung ô o2, đủ thời gian của nó
        {"at": "p1", "text": "!PHALEDO / Hũ thủy tinh vuông"},                # "p1" = lúc đoạn thuyết minh 1 bắt đầu
        {"at": "p1+1.6", "text": "Gom gọn, / !^nhìn là thấy"},
        {"at": 12.0, "dur": 1.8, "text": "!Nắp tre", "x": 0.3, "y": 0.4},     # chèn mới trên hình
      ]}

Markup y như `cap()` của cut.py: dòng cách nhau " / "; đầu dòng `!` cụm khoá đậm · `!!` khoá nghiêng · `~` chữ mảnh to ·
`.` dòng phụ nhỏ · không dấu = dòng thường; thêm `^` = hộp / màu nhấn của shop.
"""

import json
import math
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np

from studio import config

STYLE_BY_BRAND = {"PHALEDO": "phaledo-tap-chi"}
STYLE_DEFAULT = "san-pham-thuan"
STAGGER = 0.07        # mỗi từ vào cách nhau (cả khối vào ≤ 0,55s)
EXIT_GAP = 0.30       # khối cũ rút xong rồi khối mới mới vào
READ_PER_WORD, READ_MIN = 0.2, 0.7   # chữ đi CÙNG lời đọc (nghe + nhìn) → ngắn hơn ô chữ câm của bản cũ (0,25 / 0,8)
SAFE = (0.04, 0.07, 0.96, 0.975)     # khung 3:4 Shopee: chỉ chừa mép (không có cột nút TikTok)
PLATE_IN, PLATE_OUT = 0.24, 0.2


class CapsError(ValueError):
    pass


def enabled(edl: dict) -> bool:
    c = edl.get("caps")
    return isinstance(c, dict) and bool(c.get("items")) and c.get("mode") != "off"


def parse(markup: str) -> list[dict]:
    """Markup → các dòng {role, italic, accent, toks}. Cùng luật với cutlib.Cut._parse (không có phần khớp lời)."""
    lines = []
    for raw in [x.strip() for x in re.split(r"\s/\s|\n", markup) if x.strip()]:
        m = re.match(r"^([!~.^]*)\s*(.*)$", raw)
        pre, body = m.group(1), m.group(2)
        role = "key" if "!" in pre else "big" if "~" in pre else "sub" if "." in pre else "live"
        toks = [t for t in body.split() if t]
        if toks:
            lines.append({"role": role, "italic": pre.count("!") >= 2, "accent": "^" in pre, "toks": toks})
    return lines


def plain(markup: str) -> str:
    return " ".join(t for ln in parse(markup) for t in ln["toks"])


def _when(v, pieces: list[dict], end: bool = False) -> float:
    """Giây, hoặc "p3" / "p3+0.8" / "p3-0.2" = lúc đoạn thuyết minh thứ 3 BẮT ĐẦU (narration.json); "p3e" = lúc đọc
    xong. Dùng cho `until` thì "p3" = lúc đoạn 3 đọc xong."""
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"^p(\d+)(e)?\s*([+-]\s*[\d.]+)?$", str(v).strip())
    if not m:
        raise CapsError(f"caps: mốc '{v}' không hiểu (giây, 'p2', 'p2+0.8', 'p2e' = lúc đoạn 2 đọc xong)")
    k = int(m.group(1))
    if k >= len(pieces):
        raise CapsError(f"caps: mốc '{v}' — thuyết minh chỉ có {len(pieces)} đoạn (chạy `vs.py narrate` trước khi render)")
    base = pieces[k]["end"] if (m.group(2) or end) else pieces[k]["start"]
    return round(base + float((m.group(3) or "0").replace(" ", "")), 3)


def _hex(h: str) -> tuple[float, float, float]:
    """#rrggbb → (b, g, r) 0..1."""
    h = h.lstrip("#")
    return int(h[4:6], 16) / 255, int(h[2:4], 16) / 255, int(h[0:2], 16) / 255


def _plate_cfg(edl: dict, kit: dict) -> dict:
    """Badge theo SHOP: shop.json `caps.plate` (bộ nhận diện) → `edl.caps.plate` ghi đè. Shop chưa có bộ: PHALEDO-kiểu
    nền tối + nét màu nhấn, shop khác nền màu chính + nét trắng."""
    pal, brand = {}, (edl.get("brand") or "").upper()
    try:
        from studio.templates import shop_profile
        pal = shop_profile(edl["shop"]).get("palette") or {} if edl.get("shop") else {}
    except Exception:
        pal = {}
    dark = brand == "PHALEDO" or not pal
    base = {"bg": pal.get("dark", "#161616") if dark else pal.get("primary", "#161616"), "alpha": 0.93,
            "line": pal.get("accent", "#b89a6a") if dark else "#ffffff", "line_alpha": 0.5, "radius": 0.2,
            "shadow": 0.0, "motion": "fade"}
    return {**base, **(kit.get("plate") or {}), **((edl.get("caps") or {}).get("plate") or {})}


def plan(job_dir: Path, edl: dict, meta: dict, clean_rep: dict | None = None) -> dict | None:
    """Khối chữ theo định dạng của trang kinetic + cấu hình phong cách. clean_rep = báo cáo của clean.py (vùng chữ Trung
    đã xoá + khung dải)."""
    if not enabled(edl):
        return None
    from studio.edit import styles
    cfg = edl["caps"]
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    brand = (edl.get("brand") or "").upper()
    from studio.templates import shop_caps
    kit = shop_caps(edl.get("shop"))   # bộ nhận diện của shop: style + skin chữ + badge (+ khung dải, clean.py đọc)
    sid = cfg.get("style") or kit.get("style") or STYLE_BY_BRAND.get(brand, STYLE_DEFAULT)
    st = styles.resolve(styles.load(sid), edl.get("shop"))
    # khung Shopee 3:4 / 1:1 không có cột nút TikTok bên phải → dòng chữ được rộng hơn (9:16 giữ 74–76% của phong cách)
    wide = {"maxWidth": 0.88} if W / H > 0.62 else {}
    skin = {**st["skin"], **wide, **(kit.get("skin") or {}), **(cfg.get("skin") or {})}
    if (kit.get("skin") or {}).get("box") and not (cfg.get("skin") or {}).get("boxText"):
        skin["boxText"] = kit["skin"].get("boxText", skin.get("boxText"))
    npath = job_dir / "narration.json"
    pieces = json.loads(npath.read_text(encoding="utf-8")).get("pieces", []) if npath.exists() else []
    regs = {r["id"]: r for r in (clean_rep or {}).get("regions", [])}
    panels = {p["side"]: p for p in (clean_rep or {}).get("panels", [])}
    cuts = (clean_rep or {}).get("cuts", [])
    exit_def = cfg.get("exit") or st["captions"].get("exit", "rise")
    items = [dict(it) for it in cfg["items"] if not it.get("skip")]
    for n, it in enumerate(items):
        reg = regs.get(it["over"]) if it.get("over") else None
        if it.get("over") and not reg:
            raise CapsError(f"caps #{n + 1}: over='{it['over']}' — không có vùng chữ Trung đã xoá mang id đó "
                            f"(có: {', '.join(regs) or 'chưa bật edl.clean'})")
        it["_reg"] = reg
        # badge lấp vùng xoá: mặc định cho chữ Trung giữa khung (đã nhoè); vùng nằm trong khung dải thì không cần
        it["_plate"] = bool(reg) and reg.get("t0") is not None and it.get("plate", reg["method"] != "panel")
        if it.get("at") is None:
            if not it["_plate"]:
                raise CapsError(f"caps #{n + 1} '{it.get('text', '')}': thiếu `at` (chỉ khối `over` có badge mới tự lấy mốc)")
            it["_t0"] = reg["t0"] + 0.03   # chữ Việt bật lên đúng lúc chữ Trung gốc bật lên
        else:
            it["_t0"] = max(0.0, _when(it["at"], pieces))
    items.sort(key=lambda it: it["_t0"])
    free = [it for it in items if not it["_plate"]]   # khối thường: nối đuôi nhau; khối badge theo vùng chữ Trung
    blocks, warns = [], []
    for n, it in enumerate(items):
        lines = parse(it["text"])
        toks = sum(len(ln["toks"]) for ln in lines)
        if not toks:
            raise CapsError(f"caps #{n + 1}: chữ trống")
        t0, reg = it["_t0"], it["_reg"]
        stg = min(float(it.get("stagger", STAGGER)), 0.55 / max(1, toks - 1))
        k = 0
        for ln in lines:
            ln["words"] = []
            for tok in ln.pop("toks"):
                ln["words"].append({"text": tok, "t": round(t0 + k * stg, 3)})
                k += 1
        full_at = t0 + (toks - 1) * stg + 0.25
        floor = max(READ_MIN, READ_PER_WORD * toks)
        if it.get("until") is not None:
            end = _when(it["until"], pieces, end=True)
        elif it.get("dur"):
            end = t0 + float(it["dur"])
        elif it["_plate"]:
            # chữ Trung hết ĐÚNG mối cắt cảnh → chữ Việt + badge đứng tới mối cắt rồi tắt cứng (rút êm sẽ vương sang
            # cảnh sau); hết giữa cảnh → chữ rút xong lúc chữ Trung tắt, badge mờ ra ngay sau đó
            it["_hard_out"] = reg["t1"] >= dur - 0.05 or any(abs(c - reg["t1"]) <= 0.05 for c in cuts)
            end = reg["t1"] - (0.012 if it["_hard_out"] else 0.36)
        else:   # đứng tới sát khối kế (màn hình luôn có chữ — tắt tiếng vẫn hiểu), tối đa 4,5s
            j = next(i for i, f in enumerate(free) if f is it)
            nxt = free[j + 1]["_t0"] if j + 1 < len(free) else None
            end = min(nxt - EXIT_GAP if nxt is not None else dur - 0.25, t0 + 4.5)
        end = round(min(end, dur - 0.05), 3)
        if end - full_at < floor - 0.05:
            warns.append(f"'{plain(it['text'])}' {t0:.2f}–{end:.2f}s: đọc được {max(0, end - full_at):.2f}s, cần ~{floor:.1f}s "
                         f"→ rút chữ / dời khối kế")
        band = panels.get(it.get("band", "bottom"))
        on_band = False
        x = float(it.get("x", cfg.get("x", 0.5)))
        if it.get("y") is not None:
            y = float(it["y"])
        elif band and not reg:
            y = (band["y0"] + band["y1"]) / 2 / H
            spans = band.get("spans")   # None = khung khoá suốt video
            on_band = spans is None or any(a - 0.05 <= t0 and end <= z + 0.25 for a, z in spans)
            if not on_band:
                warns.append(f"'{plain(it['text'])}' {t0:.2f}–{end:.2f}s nằm ngoài lúc khung dải hiện "
                             f"({', '.join(f'{a:.1f}–{z:.1f}s' for a, z in spans)}) → chữ đứng trên hình (có bóng)")
        else:
            y = float(cfg.get("y", 0.9))
        b = {"id": f"v{n + 1:02d}", "end": end, "card": False, "light": False,
             "exit": "cut" if it.get("_hard_out") and it.get("until") is None else it.get("exit", exit_def),
             "lines": lines, "align": it.get("align", cfg.get("align", "center")), "x": x, "y": y, "rot": 0.0,
             "scale": float(it.get("scale", 1.0)) * float(cfg.get("scale", 1.0)), "fit": None, "plate": None,
             "grow": (0.9 * W, 0.72 * (band["y1"] - band["y0"])) if on_band and it.get("scale") is None else None,
             "first": t0, "full_at": round(full_at, 3), "text": plain(it["text"]), "markup": it["text"],
             "scrim": 0 if on_band else it.get("scrim", cfg.get("scrim", "auto"))}
        if reg:
            cx, cy, rw, rh, ang = reg["rect"]
            b["x"], b["y"] = float(it.get("x", cx / W)), float(it.get("y", cy / H)) + float(it.get("dy", 0.0))
            if on := panels.get("bottom" if cy > H / 2 else "top"):
                on_band = reg["method"] == "panel" and on["y0"] <= cy <= on["y1"]
            if it["_plate"]:
                b.update(rot=ang, scrim=0, fit=(rw * 0.84, rh * 0.66), align="center",
                         plate={"rect": [cx, cy, rw, rh, ang], "t0": reg["t0"], "t1": reg["t1"],
                                "hard_in": reg["t0"] <= 0.02 or any(abs(c - reg["t0"]) <= 0.05 for c in cuts),
                                "hard_out": bool(it.get("_hard_out"))})
            elif on_band:
                b["scrim"] = 0
        blocks.append(b)
    return {"style": sid, "page": st["page"], "skin": skin, "blocks": blocks, "warnings": warns,
            "plate": _plate_cfg(edl, kit)}


def _js(blocks: list[dict], flat: bool = False) -> list[dict]:
    keep = ("id", "end", "exit", "card", "light", "align", "x", "y", "scale")
    return [{**{k: b[k] for k in keep}, "rot": 0.0 if flat else b["rot"],
             "lines": [{"role": ln["role"], "italic": ln["italic"], "accent": ln["accent"],
                        "words": [{"text": w["text"], "t": w["t"]} for w in ln["words"]]} for ln in b["lines"]]}
            for b in blocks]


def _nudge(blocks: list[dict], boxes: list[dict], W: int, H: int) -> bool:
    """Khối tràn mép an toàn → dời tâm vào trong (khối trên badge giữ nguyên chỗ). Trả True nếu có dời (phải đo lại)."""
    moved = False
    x0, y0, x1, y1 = SAFE[0] * W, SAFE[1] * H, SAFE[2] * W, SAFE[3] * H
    for b, bx in zip(blocks, boxes):
        if b["plate"]:
            continue
        dx = max(0, x0 - bx["x"]) - max(0, bx["x"] + bx["w"] - x1)
        dy = max(0, y0 - bx["y"]) - max(0, bx["y"] + bx["h"] - y1)
        if abs(dx) >= 1 or abs(dy) >= 1:
            b["x"], b["y"] = b["x"] + dx / W, b["y"] + dy / H
            moved = True
    return moved


def _scrim(bx: dict, W: int, H: int) -> tuple[np.ndarray, int, int]:
    """Bóng tối mềm sau khối chữ (alpha 0..1, chưa nhân độ đậm): hình chữ nhật bo tròn nhoè rộng — không thành hộp."""
    px, py = int(bx["w"] * 0.16 + 0.03 * H), int(bx["h"] * 0.30 + 0.022 * H)
    x0, y0 = max(0, bx["x"] - px), max(0, bx["y"] - py)
    x1, y1 = min(W, bx["x"] + bx["w"] + px), min(H, bx["y"] + bx["h"] + py)
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    ix, iy = int(px * 0.55), int(py * 0.55)
    m[iy:m.shape[0] - iy, ix:m.shape[1] - ix] = 1.0
    m = cv2.GaussianBlur(m, (0, 0), max(4.0, min(px, py) * 0.42))
    return m, x0, y0


def _plate_img(rect: list, pc: dict, W: int, H: int) -> dict:
    """Badge: hình chữ nhật bo góc XOAY cùng góc dòng chữ Trung, phủ kín vùng đã xoá. Theo bộ nhận diện của shop:
    nền 1 màu hoặc chuyển màu dọc theo dòng chữ (`bg` → `bg2`), nét viền trong (`line`), thanh nhấn mép đầu dòng (`bar`),
    bóng đổ mềm (`shadow`). Trả {"img": BGRA 0..1 đã cắt gọn (gồm bóng), "x", "y", "u": vị trí dọc dòng chữ 0..1 từng
    điểm (cho hiệu ứng quét), "dir": hướng dòng chữ, "w": bề dài badge}."""
    cx, cy, rw, rh, ang = rect
    ss = 3   # vẽ to 3× rồi thu → mép mịn
    bw, bh = int(rw * ss) + 4, int(rh * ss) + 4
    box, edge = np.zeros((bh, bw), np.uint8), np.zeros((bh, bw), np.uint8)
    x1, y1 = bw - 3, bh - 3
    rr = int(max(2.0, min(rh * float(pc.get("radius", 0.2)), rh / 2)) * ss)
    cv2.rectangle(box, (2 + rr, 2), (x1 - rr, y1), 255, -1)
    cv2.rectangle(box, (2, 2 + rr), (x1, y1 - rr), 255, -1)
    for px, py in ((2 + rr, 2 + rr), (x1 - rr, 2 + rr), (2 + rr, y1 - rr), (x1 - rr, y1 - rr)):
        cv2.circle(box, (px, py), rr, 255, -1, cv2.LINE_AA)
    th = max(ss, round(0.0022 * H * ss))
    i = th // 2 + ss
    cv2.line(edge, (2 + rr, 2 + i), (x1 - rr, 2 + i), 255, th, cv2.LINE_AA)
    cv2.line(edge, (2 + rr, y1 - i), (x1 - rr, y1 - i), 255, th, cv2.LINE_AA)
    cv2.line(edge, (2 + i, 2 + rr), (2 + i, y1 - rr), 255, th, cv2.LINE_AA)
    cv2.line(edge, (x1 - i, 2 + rr), (x1 - i, y1 - rr), 255, th, cv2.LINE_AA)
    for (px, py), a0 in (((2 + rr, 2 + rr), 180), ((x1 - rr, 2 + rr), 270), ((x1 - rr, y1 - rr), 0), ((2 + rr, y1 - rr), 90)):
        cv2.ellipse(edge, (px, py), (max(1, rr - i), max(1, rr - i)), 0, a0, a0 + 90, 255, th, cv2.LINE_AA)
    # màu nền: chuyển màu dọc theo dòng chữ + đáy sậm hơn đỉnh một chút (khối có chiều sâu, không bệt)
    c0 = np.array(_hex(pc["bg"]), np.float32)
    c1 = np.array(_hex(pc.get("bg2") or pc["bg"]), np.float32)
    gx = np.linspace(0, 1, bw, dtype=np.float32)[None, :, None]
    gy = np.linspace(0, 1, bh, dtype=np.float32)[:, None, None]
    col = (c0 * (1 - gx) + c1 * gx) * (1.0 + float(pc.get("depth", 0.07)) * (0.5 - gy))
    bar = pc.get("bar")
    if bar:   # thanh nhấn ở đầu dòng (nằm trong hình bo góc)
        wbar = max(ss * 2, int(float(bar.get("w", 0.08)) * rh * ss))
        col[:, :2 + wbar] = np.array(_hex(bar["color"]), np.float32)
    la = edge.astype(np.float32)[..., None] / 255 * float(pc.get("line_alpha", 0.5))
    col = col * (1 - la) + np.array(_hex(pc.get("line") or pc["bg"]), np.float32) * la
    M = cv2.getRotationMatrix2D((bw / 2, bh / 2), -ang, 1.0)   # cv2: góc dương = ngược chiều kim
    M[0, 2] += cx * ss - bw / 2
    M[1, 2] += cy * ss - bh / 2
    big = (W * ss, H * ss)
    m = cv2.resize(cv2.warpAffine(box, M, big, flags=cv2.INTER_LINEAR), (W, H), interpolation=cv2.INTER_AREA)
    col = cv2.resize(cv2.warpAffine(np.clip(col, 0, 1), M, big, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE),
                     (W, H), interpolation=cv2.INTER_AREA)
    m = m.astype(np.float32) / 255
    sh_k = float(pc.get("shadow", 0.0))
    shadow = np.zeros_like(m)
    if sh_k > 0:   # bóng đổ mềm, lệch xuống ~6% chiều cao badge
        dy = max(1, round(rh * 0.06))
        shadow[dy:] = m[:-dy]
        shadow = cv2.GaussianBlur(shadow, (0, 0), max(2.0, rh * 0.11)) * sh_k
    alpha = m * float(pc.get("alpha", 0.93))
    out_a = alpha + shadow * (1 - alpha)
    ys, xs = np.nonzero(out_a > 0.004)
    x0, y0, xb, yb = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    img = np.zeros((yb - y0, xb - x0, 4), np.float32)
    a, oa = alpha[y0:yb, x0:xb, None], out_a[y0:yb, x0:xb, None]
    img[..., :3] = np.where(oa > 1e-4, col[y0:yb, x0:xb] * a / np.maximum(oa, 1e-4), 0)   # bóng = đen
    img[..., 3:4] = oa
    t = math.radians(ang)
    dx, dy = math.cos(t), math.sin(t)
    yy, xx = np.mgrid[y0:yb, x0:xb].astype(np.float32)
    u = ((xx - cx) * dx + (yy - cy) * dy) / max(1.0, rw) + 0.5
    return {"img": img, "x": x0, "y": y0, "u": u, "dir": (dx, dy), "w": rw}


def _plate_paint(canvas: np.ndarray, pl: dict, kin: float, kout: float, motion: str) -> None:
    """Vẽ badge lên canvas. kin 0→1 = đang VÀO (trước lúc chữ Trung xuất hiện, trên hình sạch) theo kiểu của shop:
    pop (bật nảy nhẹ) · wipe (quét dọc dòng chữ) · slide (trượt dọc dòng chữ) · fade. kout < 1 = đang mờ ra."""
    img, x0, y0 = pl["img"], pl["x"], pl["y"]
    H, W = canvas.shape[:2]
    k = kout
    if kin < 0.999:
        e = 1 - (1 - kin) ** 3   # ease-out
        if motion == "pop":
            back = 1 + 2.0 * (kin - 1) ** 3 + 1.0 * (kin - 1) ** 2   # ease-out-back nhẹ (vọt ~4%)
            s = 0.86 + 0.14 * back
            h, w = img.shape[:2]
            M = np.float32([[s, 0, (1 - s) * w / 2], [0, s, (1 - s) * h / 2]])
            img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)
            k *= min(1.0, kin * 2.2)
        elif motion == "wipe":
            img = img.copy()
            img[..., 3] *= np.clip((e * 1.22 - pl["u"]) / 0.22, 0, 1)
        elif motion == "slide":
            off = -(1 - e) * 0.09 * pl["w"]
            x0, y0 = int(round(x0 + off * pl["dir"][0])), int(round(y0 + off * pl["dir"][1]))
            k *= min(1.0, kin * 1.8)
        else:
            k *= _ease(kin)
    # cắt phần ra ngoài khung
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = min(img.shape[1], W - x0), min(img.shape[0], H - y0)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    _over(canvas[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1], img[sy0:sy1, sx0:sx1], k)


def _over(dst: np.ndarray, src: np.ndarray, k: float = 1.0) -> None:
    """Đè src (BGRA alpha thẳng, 0..1) lên dst (cùng cỡ, alpha thẳng), src nhân thêm độ đậm k."""
    sa, da = src[..., 3:4] * k, dst[..., 3:4]
    oa = sa + da * (1 - sa)
    dst[..., :3] = np.where(oa > 1e-4, (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-4), 0)
    dst[..., 3:4] = oa


def _luma(frame: np.ndarray, bx: dict) -> float:
    crop = frame[max(0, bx["y"]):bx["y"] + bx["h"], max(0, bx["x"]):bx["x"] + bx["w"]]
    return float(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).mean()) if crop.size else 128.0


def _ease(k: float) -> float:
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


def _plate_k(pt: dict, t: float) -> tuple[float, float]:
    """(độ vào, độ ra) của badge lúc t. Đục 100% suốt [t0, t1] (lúc vùng bên dưới đang nhoè): VÀO xong trước t0 và mờ RA
    sau t1 — tức trên hình sạch, không bao giờ để lộ mảng nhoè; mép trùng mối cắt cảnh / đầu video thì bật-tắt cứng."""
    if pt["hard_in"]:
        kin = 1.0 if t >= pt["t0"] - 0.001 else 0.0
    else:
        kin = min(1.0, max(0.0, (t - (pt["t0"] - PLATE_IN)) / PLATE_IN))
    if pt["hard_out"]:
        kout = 1.0 if t < pt["t1"] - 0.001 else 0.0
    else:
        kout = _ease((pt["t1"] + PLATE_OUT - t) / PLATE_OUT)
    return kin, kout


def build(job_dir: Path, edl: dict, meta: dict, video: Path, clean_rep: dict | None = None) -> dict | None:
    """Dựng lớp chữ Việt động → `caps.mov` (QuickTime RLE có alpha, đúng cỡ + fps + thời lượng video chính).
    Trả {"mov", "boxes" (vùng chữ cho logo / watermark né), "blocks", "warnings", "style"}."""
    p = plan(job_dir, edl, meta, clean_rep)
    if not p:
        return None
    from studio.edit.kinetic import Kinetic
    W, H, fps, dur = meta["width"], meta["height"], meta["fps"], meta["duration"]
    blocks = p["blocks"]
    work = job_dir / "caps"
    with Kinetic(p["page"], W, H, p["skin"]) as kin:
        boxes = kin.load(_js(blocks, flat=True))
        again = False
        for b, bx in zip(blocks, boxes):   # khối trên badge: phóng / thu cho vừa badge (đo lúc chưa xoay)
            if b["fit"]:
                k = min(b["fit"][0] / max(1, bx["w"]), b["fit"][1] / max(1, bx["h"]))
                b["scale"] = round(b["scale"] * float(np.clip(k, 0.6, 2.6)), 3)
                again = True
            elif b["grow"]:   # khối trên khung dải: phóng cho đầy ~60% chiều cao khung (không thu nhỏ, tối đa 1,45×)
                k = min(b["grow"][0] / max(1, bx["w"]), b["grow"][1] / max(1, bx["h"]))
                b["scale"] = round(b["scale"] * float(np.clip(k, 1.0, 1.45)), 3)
                again = True
        if again:
            boxes = kin.load(_js(blocks, flat=True))
        if _nudge(blocks, boxes, W, H):
            again = True
        boxes = kin.load(_js(blocks))
        index = kin.frames(dur, fps, work)
    for b, bx in zip(blocks, boxes):
        b["rect"] = [bx["x"], bx["y"], bx["w"], bx["h"]]
        if b["plate"]:   # vùng chiếm chỗ = cả badge
            px, py, pw, ph, _ = b["plate"]["rect"]
            r = cv2.boxPoints(((px, py), (pw, ph), b["plate"]["rect"][4]))
            b["rect"] = [int(r[:, 0].min()), int(r[:, 1].min()), int(np.ptp(r[:, 0])), int(np.ptp(r[:, 1]))]
    for b in blocks:   # badge lấn vào khối chữ khác (thường là badge nghiêng thò xuống khung dải) → báo để dời khối
        for o in blocks:
            if o is b or not o["plate"] or b["plate"]:
                continue
            ix = min(b["rect"][0] + b["rect"][2], o["rect"][0] + o["rect"][2]) - max(b["rect"][0], o["rect"][0])
            iy = min(b["rect"][1] + b["rect"][3], o["rect"][1] + o["rect"][3]) - max(b["rect"][1], o["rect"][1])
            if ix > 4 and iy > 4 and b["first"] < o["plate"]["t1"] and b["end"] > o["plate"]["t0"]:
                p["warnings"].append(f"'{b['text']}' ({b['first']:.2f}s) bị badge '{o['text']}' lấn {ix}×{iy}px → dời x / y "
                                     f"khối này hoặc cho hiện sau {o['plate']['t1']:.2f}s")
    # độ đậm bóng sau chữ đặt trên hình: nền càng sáng càng cần (đo khung giữa khối trên nguồn đã xoá chữ Trung)
    cap = cv2.VideoCapture(str(video))
    scrims, plates = [], []
    for b, bx in zip(blocks, boxes):
        s = b["scrim"]
        if s == "auto":
            cap.set(cv2.CAP_PROP_POS_MSEC, (b["first"] + b["end"]) / 2 * 1000)
            ok, fr = cap.read()
            s = float(np.clip((_luma(fr, bx) - 70) / 330, 0.12, 0.36)) if ok else 0.26
        b["scrim"] = round(float(s), 2)
        scrims.append(_scrim(bx, W, H) if b["scrim"] > 0 else None)
        plates.append(_plate_img(b["plate"]["rect"], p["plate"], W, H) if b["plate"] else None)
    cap.release()
    mov = job_dir / "caps.mov"
    cmd = [config.FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", f"{fps}",
           "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", str(mov)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    cache: dict[str, np.ndarray] = {}
    empty = np.zeros((H, W, 4), np.uint8).tobytes()
    try:
        for i, ent in enumerate(index):
            t = i / fps
            live_s = [(b, sc) for b, sc in zip(blocks, scrims) if sc is not None and b["first"] - 0.12 <= t <= b["end"] + 0.3]
            live_p = [(b, pl) for b, pl in zip(blocks, plates) if pl is not None
                      and min(_plate_k(b["plate"], t)) > 0.001]
            if ent is None and not live_s and not live_p:
                proc.stdin.write(empty)
                continue
            canvas = np.zeros((H, W, 4), np.float32)
            for b, (m, x0, y0) in live_s:        # bóng đen mềm (cộng dồn kiểu lấy lớn nhất)
                k = _ease((t - (b["first"] - 0.12)) / 0.3) * _ease((b["end"] + 0.3 - t) / 0.3)
                reg = canvas[y0:y0 + m.shape[0], x0:x0 + m.shape[1], 3]
                np.maximum(reg, m * b["scrim"] * k, out=reg)
            for b, pl in live_p:                 # badge lấp vùng đã xoá — vào theo kiểu của shop, đứng suốt lúc có chữ Trung
                _plate_paint(canvas, pl, *_plate_k(b["plate"], t), p["plate"].get("motion", "fade"))
            if ent is not None:
                name, x, y = ent
                if name not in cache:
                    if len(cache) > 240:
                        cache.clear()
                    cache[name] = cv2.imread(str(work / name), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
                png = cache[name]
                h, w = min(png.shape[0], H - y), min(png.shape[1], W - x)
                _over(canvas[y:y + h, x:x + w], png[:h, :w])
            proc.stdin.write((np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    finally:
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0:
            raise RuntimeError(f"Ghi caps.mov lỗi: {err[-600:]}")
    out_boxes = [{"x": b["rect"][0], "y": b["rect"][1], "w": b["rect"][2], "h": b["rect"][3],
                  "start": b["plate"]["t0"] - PLATE_IN if b["plate"] else b["first"],
                  "end": b["plate"]["t1"] + PLATE_OUT if b["plate"] else b["end"] + 0.3} for b in blocks]
    for w in p["warnings"]:
        print(f"  ⚠ chữ Việt: {w}")
    print(f"  chữ Việt động: {len(blocks)} khối ({sum(1 for b in blocks if b['plate'])} trên badge lấp chữ Trung), "
          f"phong cách {p['style']} → caps.mov")
    return {"mov": mov, "boxes": out_boxes, "blocks": blocks, "warnings": p["warnings"], "style": p["style"]}
