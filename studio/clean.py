"""XOÁ chữ Trung đồ hoạ khỏi nguồn (Việt hoá V2, Sếp 11/11) → `source-clean.mp4`.

Bản cũ: ô chữ Việt vừa CHE vừa HIỂN THỊ → phải đục 100% và to bằng (hoặc hơn) ô chữ Trung: phụ đề cao ~40px bị thay
bằng viên đen 720×134. V2 tách đôi: module này lo XOÁ (dù lớp chữ Việt có lệch / vào trễ cũng không lộ chữ Trung),
chữ Việt đặt tự do ở lớp riêng (`studio/vcaps.py`), nhỏ gọn, không cần nền.

Ba cách xoá (mỗi ô che chữ Trung trong `edl.overlays`, tự chọn hoặc ép bằng `overlay["clean"]`):
- `fill`  — dòng chữ ngang, hẹp (phụ đề đáy): dò nét chữ thật từng khung → nội suy nền từ viền quanh + nhoè nhẹ.
            Gần như mất dấu; hình xoá = đúng vùng nét chữ, không phải ô Gemini (ô Gemini lệch / dư).
- `blur`  — sticker to / chữ xoay: nhoè mạnh trong hình chữ nhật XOAY cùng góc ôm nét chữ, mép mềm (kính mờ).
- `none`  — không đụng (chữ sẽ bị cảnh khác che, hoặc chủ ý giữ).
Thời điểm xoá bám theo NÉT CHỮ dò được từng khung (nới ±0,1s) chứ không tin mốc `start/end` của Gemini (hay lệch vài
trăm ms). Ô dò được < 50% số khung (chữ không phải kiểu sáng-viền-tối) → lùi về ô tĩnh theo mốc + nhoè, có cảnh báo.

KHUNG DẢI đáy / đỉnh (Sếp 11/11, sau khi xem bản vá nền: "vẫn thấy dấu hiệu làm mờ → biết là edit lại"): chữ Trung nằm
ở dải ĐÁY (tâm > 78% H) hoặc dải ĐỈNH (< 22% H) thì KHÔNG vá từng dòng — phủ hẳn một KHUNG lấp cả dải (nền = phần hình
kề bên lật gương, nhoè mạnh + tối; mép sắc như khung có chủ ý), chữ Việt đặt trên khung. Khung CHỈ HIỆN KHI CÓ CHỮ TRUNG
(Sếp 11/11: "không lock từ đầu tới cuối"): vào sớm 0,25s trước dòng chữ Trung đầu (có mối cắt cảnh sát đó thì bật đúng
mối cắt), giữ liền qua các khe < 0,8s giữa hai dòng, mờ ra sau khi dòng cuối tắt. Mặc định tự bật; tắt: `edl.clean = {"mode": "auto", "bottom": "fill", "top": "fill"}`.
Chỉnh: `edl.clean.panel = {"dim": 0.5, "line": "#b89a6a", "hold": true}` (`hold` = khoá khung suốt video).
Chữ ở GIỮA khung vẫn xoá bằng `blur`, và lớp chữ Việt PHẢI đặt badge nền đục che kín đúng vùng đó (`caps.items[].over`)
— không để lộ mảng nhoè.

`edl.clean.bands = [{"y0": 0.86, "y1": 1.0, "start", "end", "mode": "panel"|"blur"|"dim", "dim": 0.25}]` — khai tay
một dải (khung lấp / làm mờ / tối) khi cần.
"""

import hashlib
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

from studio import config, media
from studio.templates import shop_caps

OUT = "source-clean.mp4"
PAD_T = 0.35         # dò nét chữ rộng hơn mốc Gemini mỗi đầu
GROW = 3             # nới khoảng có chữ ±3 khung (chữ Trung mờ dần vào/ra)
MIN_SEEN = 0.5       # dò thấy nét ở ≥ 50% khung trong mốc mới tin bộ dò
PANEL_GAP = 0.8      # hai dòng chữ Trung cách nhau < 0,8s → khung dải giữ liền
PANEL_LEAD = 0.25    # khung dải vào sớm trước dòng chữ Trung đầu
PANEL_FADE = 0.2
COVER_MAX = 0.22     # một nhóm chữ Trung phủ > 22% diện tích khung → badge che quá to, phải cân nhắc phương án khác
PANEL_MAX = 0.17     # khung dải chỉ được cắt tối đa 17% chiều cao khung (Sếp 11/11, video 0374: phụ đề ở 17–21% H mà
#                      phủ khung dải thì mất gần 1/4 khung → "không được"); quá ngưỡng → badge che ôm chữ
VERSION = 20


def enabled(edl: dict) -> bool:
    c = edl.get("clean")
    return bool(c) and c != "off" and not (isinstance(c, dict) and c.get("mode") == "off")


def _cfg(edl: dict) -> dict:
    c = edl.get("clean")
    return c if isinstance(c, dict) else {}


def regions(edl: dict, meta: dict) -> list[dict]:
    """Các vùng cần xoá, lấy từ ô che chữ Trung của edl (bỏ ô `keep` = chữ trong cảnh; ô `skip` có zh vẫn xoá)."""
    H = meta["height"]
    default = _cfg(edl).get("method", "auto")
    out = []
    for o in edl.get("overlays", []):
        if o.get("mode") == "keep" or o.get("kind") == "scene" or not o.get("zh"):
            continue
        c = o.get("clean", default)
        c = {"method": c} if isinstance(c, str) else dict(c or {})
        method = c.get("method", default)
        if method in ("none", "off", False):
            continue
        x, y, w, h = (int(v) for v in (c.get("box") or o.get("zh_box") or o["box"]))
        angle = float(c.get("angle", o.get("zh_angle", o.get("angle") or 0.0)))
        if method == "auto":
            method = "fill" if abs(angle) < 4 and h <= 0.17 * H else "blur"
        out.append({"id": o["id"], "zh": o["zh"], "method": method, "box": [x, y, w, h], "angle": angle,
                    "start": float(c.get("start", o.get("zh_start", o["start"]))),
                    "end": float(c.get("end", o.get("zh_end", o["end"]))),
                    "detect": c.get("detect", True), "pad": int(c.get("pad", 8))})
    return out


def _rot_rect(box: list, angle: float, pad: int) -> tuple:
    x, y, w, h = box
    if abs(angle) < 0.5:
        return ((x + w / 2, y + h / 2), (w + 2 * pad, h + 2 * pad), 0.0)
    t = math.radians(abs(angle))
    c, s = math.cos(t), math.sin(t)
    det = c * c - s * s
    if det < 0.35:
        return ((x + w / 2, y + h / 2), (w + 2 * pad, h + 2 * pad), 0.0)
    a = (w * c - h * s) / det
    b = max((h * c - w * s) / det, 0.12 * a, 24)
    return ((x + w / 2, y + h / 2), (a + 2 * pad, b + 2 * pad), -angle)   # cv2: dương = thuận chiều kim đồng hồ


def _mask(shape: tuple, rect: tuple) -> np.ndarray:
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [cv2.boxPoints(rect).astype(np.int32)], 255)
    return m


_K5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
_K9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
_K2 = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))


def _glyphs(bgr: np.ndarray) -> np.ndarray:
    """Nét chữ đồ hoạ kiểu Trung: lõi SÁNG kề viền TỐI (trắng / vàng viền đen). Trả mặt nạ 0/255."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    v = bgr.max(axis=2)
    bright = (v >= 205).astype(np.uint8) * 255
    dark = (g <= 60).astype(np.uint8) * 255
    near = cv2.dilate(bright, _K5) & cv2.dilate(dark, _K5)
    return cv2.morphologyEx(near, cv2.MORPH_OPEN, _K2)


def _axes(angle: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Trục dọc theo dòng chữ (u) + vuông góc (v) trong toạ độ ảnh; angle dương = dòng chữ dốc LÊN về bên phải."""
    t = math.radians(angle)
    return (math.cos(t), -math.sin(t)), (math.sin(t), math.cos(t))


def _extent(gl: np.ndarray, x0: int, y0: int, centre: tuple, angle: float, min_pts: int) -> tuple | None:
    """Khung ôm NÉT CHỮ trong hệ trục của dòng chữ: (u0, u1, v0, v1). Dải v = các hàng có mật độ nét ≥ 25% hàng dày
    nhất (bỏ nét rời của cảnh), u = 1–99% điểm nét trong dải. Không đủ nét → None."""
    ys, xs = np.nonzero(gl)
    if len(xs) < min_pts:
        return None
    du, dv = _axes(angle)
    dx, dy = xs + x0 - centre[0], ys + y0 - centre[1]
    u, v = dx * du[0] + dy * du[1], dx * dv[0] + dy * dv[1]
    lo = v.min()
    hist = np.bincount(((v - lo) / 2).astype(int)).astype(np.float32)
    hist = np.convolve(hist, np.ones(5) / 5, mode="same")
    rows = np.nonzero(hist >= 0.25 * hist.max())[0]
    v0, v1 = lo + rows[0] * 2, lo + rows[-1] * 2 + 2
    inside = (v >= v0) & (v <= v1)
    if inside.sum() < min_pts:
        return None
    return float(np.percentile(u[inside], 1)), float(np.percentile(u[inside], 99)), float(v0), float(v1)


def _iou(a: tuple, b: tuple) -> float:
    iu = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    iv = max(0.0, min(a[3], b[3]) - max(a[2], b[2]))
    inter = iu * iv
    union = (a[1] - a[0]) * (a[3] - a[2]) + (b[1] - b[0]) * (b[3] - b[2]) - inter
    return inter / union if union > 0 else 0.0


def _wide_zone(r: dict, W: int, H: int) -> tuple:
    """Ô bao RỘNG quanh ô gốc của Gemini (nới 35% ngang, 60% dọc): chỗ chữ Trung có thể chạm tới lúc bật / phóng / bay
    vào (0379: chữ phóng to tràn ~40% chiều cao ô lên phía trên)."""
    x, y, w, h = r["box"]
    return (int(max(0, x - 0.35 * w)), int(max(0, y - 0.6 * h)), int(min(W, x + 1.35 * w)), int(min(H, y + 1.6 * h)))


def _scan(video: Path, regs: list[dict], fps: float) -> tuple[int, list[int]]:
    """Lượt 1: mỗi vùng, mỗi khung trong mốc nới → khung ôm nét chữ (hệ trục dòng chữ). Ghi r['seen'] {khung: extent}."""
    cap = cv2.VideoCapture(str(video))
    for r in regs:
        r["rect"] = _rot_rect(r["box"], r["angle"], r["pad"] + 6)
        r["f0"], r["f1"] = int(max(0, (r["start"] - PAD_T) * fps)), int((r["end"] + PAD_T) * fps) + 1
        r["seen"], r["cnt"], r["cntb"] = {}, {}, {}
        r["fb0"] = int(max(0, (r["start"] - 0.9) * fps))
        r["_m"] = None
    i, cuts, prev = 0, [], None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        tiny = cv2.cvtColor(cv2.resize(f, (48, 64), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.int16)
        if prev is not None:
            # đổi cảnh (cắt thẳng) — đo NGOÀI vùng chữ đang hoạt động: sticker to bật / bay vào làm cả khung đổi mạnh,
            # từng bị coi là mối cắt (0379: 0,87s · 0,93s · 2,3s) rồi chặn nhầm thời điểm xoá
            out = np.ones((64, 48), bool)
            for r in regs:
                if r["f0"] <= i <= r["f1"]:
                    if "_tiny" not in r:
                        (cx, cy), (w, h), ang = r["rect"]
                        big = _mask(f.shape, ((cx, cy), (w * 1.1, h * 1.35), ang))
                        r["_tiny"] = cv2.resize(big, (48, 64), interpolation=cv2.INTER_AREA) > 0
                    out &= ~r["_tiny"]
            d = np.abs(tiny - prev)
            if out.mean() >= 0.08 and float(d[out].mean()) > 24:
                cuts.append(i)
        prev = tiny
        for r in regs:
            if r["fb0"] <= i <= r["f1"] and r["method"] == "blur":
                if "_wide" not in r:
                    r["_wide"] = _wide_zone(r, f.shape[1], f.shape[0])
                wx0, wy0, wx1, wy1 = r["_wide"]
                r["cntb"][i] = int(cv2.countNonZero(_glyphs(f[wy0:wy1, wx0:wx1])))
            if not (r["f0"] <= i <= r["f1"]):
                continue
            if r["_m"] is None:
                m = _mask(f.shape, r["rect"])
                ys, xs = np.nonzero(m)
                r["_roi"] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
                x0, y0, x1, y1 = r["_roi"]
                r["_m"] = m[y0:y1, x0:x1]
                r["_min"] = int(max(40, 0.004 * cv2.countNonZero(r["_m"])))
            x0, y0, x1, y1 = r["_roi"]
            gl = _glyphs(f[y0:y1, x0:x1]) & r["_m"]
            r["cnt"][i] = int(cv2.countNonZero(gl))
            ext = _extent(gl, x0, y0, r["rect"][0], r["angle"], r["_min"])
            if ext:
                r["seen"][i] = ext
        i += 1
    cap.release()
    return i, cuts


def _rect_of(r: dict, ext: tuple, pad: int) -> tuple:
    """Khung (u0, u1, v0, v1) trong hệ trục dòng chữ → hình chữ nhật xoay cv2 trong toạ độ ảnh."""
    du, dv = _axes(r["angle"])
    cu, cw = (ext[0] + ext[1]) / 2, (ext[2] + ext[3]) / 2
    cx, cy = r["origin"]
    return ((cx + cu * du[0] + cw * dv[0], cy + cu * du[1] + cw * dv[1]),
            (ext[1] - ext[0] + 2 * pad, ext[3] - ext[2] + 2 * pad), -r["angle"])


def _decide(regs: list[dict], fps: float, n_frames: int, W: int, H: int, cuts: list[int]) -> list[str]:
    """Từ kết quả dò → khung nào xoá (`on`) + hình chữ nhật xoá cố định (ôm nét, xoay theo dòng chữ). Trả cảnh báo."""
    warns = []
    for r in regs:
        a, b = int(r["start"] * fps), int(r["end"] * fps)
        core = [r["seen"][i] for i in r["seen"] if a <= i <= b]
        ok, med = {}, None
        if core:
            c = np.array(core)
            med = (float(np.percentile(c[:, 0], 8)), float(np.percentile(c[:, 1], 92)),
                   float(np.median(c[:, 2])), float(np.median(c[:, 3])))
            # chỉ tin khung có khung-ôm-nét KHỚP khung chung của vùng: nét của cảnh (hũ, tay, cảnh sau mối cắt) bị loại
            ok = {i: e for i, e in r["seen"].items() if _iou(e, med) >= 0.45}
        inside = [i for i in ok if a <= i <= b]
        ratio = len(inside) / max(1, b - a + 1)
        r["seen_ratio"] = round(ratio, 2)
        if r["detect"] and med and ratio >= MIN_SEEN:
            idx = sorted(ok)
            on = set()
            for j, i in enumerate(idx):   # lấp lỗ ngắn (≤ 6 khung) + nới 2 đầu
                on.update(range(i - GROW, i + GROW + 1))
                if j and i - idx[j - 1] <= 6:
                    on.update(range(idx[j - 1], i))
            r["origin"], r["med"] = r["rect"][0], med
            hv = med[3] - med[2]
            if r["method"] == "fill":
                # chữ Trung đang BAY VÀO / bật từng chữ (lệch chỗ, to hơn) không khớp khung chung nhưng vẫn nằm đúng DẢI
                # của dòng chữ → xoá theo nét của chính khung đó (đo 0379: "维艾密封罐" trượt vào từ trái lọt 4 khung)
                r["band"] = (med[2] - 0.6 * hv, med[3] + 0.6 * hv)
                r["loose"] = {i: e for i, e in r["seen"].items()
                              if r["band"][0] <= (e[2] + e[3]) / 2 <= r["band"][1]}
                for i in r["loose"]:
                    on.update(range(i - 1, i + 2))
                # Mối cắt cảnh SÁT mốc phân tích (≤ 0,45s phía ngoài, ≤ 0,15s phía trong) = ranh thật của dòng chữ: dòng
                # kế cùng chỗ / nét của cảnh kế hay "khớp" khung chung (đo 0374: nhãn giữa cảnh o4 bị xoá sớm 0,47s lên
                # hũ cà phê của cảnh trước; hai phụ đề nối nhau chồng mốc ~1s).
                lim_a, lim_b = round(0.45 * fps), round(0.15 * fps)
                lo = max((c for c in cuts if a - lim_a <= c <= a + lim_b), default=None)
                hi = min((c for c in cuts if b - lim_b <= c <= b + lim_a), default=None)
                on = {i for i in on if (lo is None or i >= lo) and (hi is None or i < hi)}
            else:   # sticker to: vùng rộng dễ "thấy nét" của cảnh kế → không kéo qua mối cắt cảnh sát mốc
                lim = round(0.4 * fps)
                lo = max((c for c in cuts if a - lim <= c <= a + lim), default=None)
                # chữ đã có THẬT trước mối cắt (nhiều khung khớp, không chỉ phần nới) → không chặn đầu vào
                # (đo 0379: dòng hook 3 hiện từ 2,1s, "mối cắt" 2,3s → chặn nhầm làm lộ nguyên chữ Trung 5 khung)
                if lo is not None and sum(1 for i in idx if i < lo) > 2:
                    lo = None
                hi = min((c for c in cuts if b - lim <= c <= b + lim + GROW), default=None)
                on = {i for i in on if (lo is None or i >= lo) and (hi is None or i < hi)}
                # Chữ Trung BẬT / NẢY / BAY VÀO (0,2–0,4s đầu): nét to, lệch chỗ, thò ra ngoài hình chữ nhật cuối → badge
                # không che nổi (đo 0379: dòng hook 3 lộ nguyên chữ 5 khung, dòng 2 lộ bóng chữ phóng to). Cả quãng đó
                # ĐÓNG BĂNG vùng ô gốc bằng hình SẠCH của khung ngay trước khi chữ xuất hiện (không nhoè, không lộ chữ).
                # Lúc chữ BẮT ĐẦU xuất hiện = lúc số nét trong ô bao rộng vọt lên khỏi mức nền của cảnh.
                tight = [i for i in idx if _iou(ok[i], med) >= 0.75]
                stable = next((i for i in tight if all(j in tight for j in range(i, i + 4))), idx[0])
                cb = r["cntb"]
                win = [i for i in range(max(0, stable - round(0.9 * fps)), stable) if i in cb and (lo is None or i >= lo)]
                j, clean_before = stable, False
                if win:
                    okc = float(np.median([cb[i] for i in (tight or idx) if i in cb] or [0]))
                    base = float(np.percentile([cb[i] for i in win], 10))
                    thr = base + 0.25 * (okc - base)
                    if okc - base >= 0.3 * okc:
                        # khung ĐẦU TIÊN (trong 0,6s trước lúc ổn định) nét vọt khỏi nền và vọt LẠI trong 6 khung kế —
                        # không đòi liên tục. Số đo 0379: chữ CHỚP đúng 1 khung (0,833s · 2,200s), tắt / phóng to nhoè 3
                        # khung (nét tụt về mức nền), rồi mới vào lại và nảy tới ~0,3s sau.
                        near = [i for i in win if i >= stable - round(0.6 * fps)]
                        j = next((i for i in near if cb[i] > thr and any(cb.get(i + k, 0) > thr for k in range(1, 7))),
                                 stable)
                        clean_before = (j - 1) in cb and cb[j - 1] <= thr
                    else:   # nền cảnh nhiều nét, không thấy rõ lúc chữ vào → lùi 0,2s trước khung khớp đầu
                        j = max(win[0], idx[0] - round(0.2 * fps))
                if j < stable:
                    r["pre"] = set(range(j, stable))
                    r["hold_at"] = j - 1 if clean_before and j not in cuts else None
                    on = {i for i in on if i >= j} | r["pre"]
            r["on"] = {i for i in on if 0 <= i < n_frames}
            if r["method"] == "blur":   # sticker: nới hai đầu dòng 4% — dấu "?" / nét đuôi hay nằm ngoài 8–92% điểm nét
                ext_u = 0.04 * (med[1] - med[0])
                med = (med[0] - ext_u, med[1] + ext_u, med[2], med[3])
                r["med"] = med
            r["rect"] = _rect_of(r, med, r["pad"])
            r["mode"] = "dò nét"
        else:
            if r["detect"]:
                warns.append(f"{r['id']} '{r['zh']}': chỉ dò thấy nét chữ ở {ratio:.0%} khung → xoá theo Ô TĨNH + mốc Gemini "
                             f"(soát khung ±0,4s quanh {r['start']:.2f}s / {r['end']:.2f}s; QA sẽ bắt nếu sót)")
            r["on"] = set(range(int(max(0, (r["start"] - 0.15) * fps)), min(n_frames, int((r["end"] + 0.15) * fps) + 1)))
            r["rect"] = _rot_rect(r["box"], r["angle"], 4)
            r["mode"] = "ô tĩnh"
            r.pop("loose", None)
            if r["method"] == "fill":
                r["method"] = "blur"   # không biết nét ở đâu → nhoè cả ô cho chắc
        bx = cv2.boxPoints(r["rect"])
        r["hug"] = [int(max(0, bx[:, 0].min())), int(max(0, bx[:, 1].min())),
                    int(min(W, bx[:, 0].max())), int(min(H, bx[:, 1].max()))]
    return warns


def _resolve_overlaps(regs: list[dict], fps: float) -> None:
    """Hai dòng chữ Trung NỐI TIẾP cùng một chỗ (phụ đề đổi câu) đều "thấy" nét của nhau → khoảng xoá chồng lên nhau.
    Chia ranh: khung đầu tiên mà nét khớp khung chung của dòng SAU hơn dòng trước (bề rộng hai câu khác nhau); không
    phân biệt được thì lấy giữa hai mốc phân tích. Dòng hiện CÙNG LÚC (khối nhiều dòng) không đụng."""
    rs = sorted((r for r in regs if r.get("med") and r["on"] and abs(r["angle"]) < 4), key=lambda r: r["start"])
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            both = sorted(a["on"] & b["on"])
            if not both:
                continue
            ot = min(a["end"], b["end"]) - max(a["start"], b["start"])
            if ot >= 0.6 * min(a["end"] - a["start"], b["end"] - b["start"]):
                continue   # hiện cùng lúc
            (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a["hug"], b["hug"]
            if min(ax1, bx1) <= max(ax0, bx0) or min(ay1, by1) - max(ay0, by0) < 0.5 * min(ay1 - ay0, by1 - by0):
                continue   # không cùng chỗ
            cut = round((a["end"] + b["start"]) / 2 * fps)
            for k in both:
                ia = _iou(a["seen"][k], a["med"]) if k in a["seen"] else 0.0
                ib = _iou(b["seen"][k], b["med"]) if k in b["seen"] else 0.0
                if ib > ia and ib >= 0.45:
                    cut = k
                    break
            cut = min(max(cut, both[0]), both[-1] + 1)
            a["on"] = {k for k in a["on"] if k < cut}
            b["on"] = {k for k in b["on"] if k >= cut}


def _fill_masks(shape: tuple, rect: tuple) -> dict:
    H, W = shape[:2]
    bx = cv2.boxPoints(rect)
    m = 26
    c = (int(max(0, bx[:, 0].min() - m)), int(max(0, bx[:, 1].min() - m)),
         int(min(W, bx[:, 0].max() + m)), int(min(H, bx[:, 1].max() + m)))
    mask = _mask(shape, rect)[c[1]:c[3], c[0]:c[2]]
    small = cv2.resize(mask, ((c[2] - c[0] + 1) // 2, (c[3] - c[1] + 1) // 2), interpolation=cv2.INTER_NEAREST)
    return {"c": c, "small": cv2.dilate(small, _K5),
            "soft": cv2.GaussianBlur(cv2.dilate(mask, _K9), (0, 0), 5).astype(np.float32)[..., None] / 255}


def _fill(f: np.ndarray, r: dict, i: int) -> None:
    """Nội suy nền vào hình chữ nhật ôm nét chữ (từ viền quanh) + nhoè nhẹ, mép mềm. Sửa tại chỗ.
    Khung có nét lệch khỏi khung chung (chữ đang bay vào) → nới hình xoá cho ôm cả nét của khung đó."""
    if "_fm" not in r:
        r["_fm"] = _fill_masks(f.shape, r["rect"])
    k = r["_fm"]
    e = (r.get("loose") or {}).get(i)
    if e:
        med, band = r["med"], r["band"]
        ext = (min(med[0], e[0]), max(med[1], e[1]), max(band[0], min(med[2], e[2])), min(band[1], max(med[3], e[3])))
        if ext[0] < med[0] - 4 or ext[1] > med[1] + 4 or ext[2] < med[2] - 4 or ext[3] > med[3] + 4:
            k = _fill_masks(f.shape, _rect_of(r, ext, r["pad"]))
    cx0, cy0, cx1, cy1 = k["c"]
    if cx1 - cx0 < 4 or cy1 - cy0 < 4:
        return
    crop = f[cy0:cy1, cx0:cx1]
    small = cv2.resize(crop, (k["small"].shape[1], k["small"].shape[0]), interpolation=cv2.INTER_AREA)
    ip = cv2.inpaint(small, k["small"], 3, cv2.INPAINT_TELEA)
    ip = cv2.GaussianBlur(ip, (0, 0), 2.2)
    ip = cv2.resize(ip, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_CUBIC)
    crop[:] = (ip * k["soft"] + crop * (1 - k["soft"])).astype(np.uint8)


def _hold_zone(r: dict, W: int, H: int) -> tuple:
    """Vùng đóng băng lúc chữ Trung bật vào: ô bao rộng quanh ô gốc của Gemini ∪ hình chữ nhật cuối."""
    x0, y0, x1, y1 = _wide_zone(r, W, H)
    hx0, hy0, hx1, hy1 = r["hug"]
    return (max(0, min(x0, hx0 - 12)), max(0, min(y0, hy0 - 12)), min(W, max(x1, hx1 + 12)), min(H, max(y1, hy1 + 12)))


def _hold(f: np.ndarray, r: dict, k: float = 1.0) -> None:
    """Dán hình sạch đã giữ (khung trước khi chữ xuất hiện) lên vùng ô gốc, mép mềm; k < 1 = đang trả về hình thật."""
    x0, y0, x1, y1 = r["_hz"]
    if "_hs" not in r:
        H, W = f.shape[:2]
        m = np.ones((y1 - y0, x1 - x0), np.float32)
        e = 10   # mép mềm CHỈ ở cạnh nằm trong khung; cạnh chạm biên khung giữ đục (0379: mảnh chữ Trung "nhân bản"
        #          sát mép trái / phải / đáy khung lọt qua dải mép mềm 10px)
        if y0 > 0:
            m[:e] = 0
        if y1 < H:
            m[-e:] = 0
        if x0 > 0:
            m[:, :e] = 0
        if x1 < W:
            m[:, -e:] = 0
        r["_hs"] = cv2.GaussianBlur(m, (0, 0), 5, borderType=cv2.BORDER_REPLICATE)[..., None]
    a = r["_hs"] * k
    crop = f[y0:y1, x0:x1]
    crop[:] = (r["_held"] * a + crop * (1 - a)).astype(np.uint8)


def _blur_wide(f: np.ndarray, r: dict, scale: float) -> None:
    """Nhoè vùng nới rộng `scale` lần quanh hình chữ nhật của chữ (lúc chữ Trung đang bay vào phóng to). Sửa tại chỗ."""
    (cx, cy), (w, h), ang = r["rect"]
    rect = ((cx, cy), (w * (1 + (scale - 1) * 0.45), h * scale), ang)   # chữ phóng đều; bề ngang đã gần hết khung
    m = _mask(f.shape, rect)
    soft = cv2.GaussianBlur(m, (0, 0), max(8.0, 0.12 * h * scale))
    ys, xs = np.nonzero(soft > 2)
    if not len(xs):
        return
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    a = np.clip(soft[y0:y1, x0:x1].astype(np.float32) / 255 * 1.5, 0, 1)[..., None]
    crop = f[y0:y1, x0:x1]
    k = 8
    small = cv2.resize(crop, (max(2, crop.shape[1] // k), max(2, crop.shape[0] // k)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(3.0, 0.42 * h * scale / k))
    bl = cv2.resize(small, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
    crop[:] = (bl * a + crop * (1 - a)).astype(np.uint8)


def _blur(f: np.ndarray, r: dict) -> None:
    """Nhoè mạnh trong hình chữ nhật xoay, mép mềm (kính mờ). Sửa tại chỗ."""
    if "_soft" not in r:
        rect = r["rect"]
        m = _mask(f.shape, rect)
        short = min(rect[1])
        r["_sigma"] = max(14.0, 0.34 * short)
        feather = max(6.0, 0.10 * short)
        soft = cv2.GaussianBlur(m, (0, 0), feather)
        ys, xs = np.nonzero(soft > 2)
        r["_bb"] = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        x0, y0, x1, y1 = r["_bb"]
        # mép mềm nhưng lõi vẫn đục hẳn: kéo đường cong lên để vùng chữ (bên trong hình chữ nhật) là 100% nhoè
        r["_soft"] = np.clip(soft[y0:y1, x0:x1].astype(np.float32) / 255 * 1.6, 0, 1)[..., None]
    x0, y0, x1, y1 = r["_bb"]
    crop = f[y0:y1, x0:x1]
    k = 4
    small = cv2.resize(crop, (max(2, crop.shape[1] // k), max(2, crop.shape[0] // k)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), r["_sigma"] / k)
    bl = cv2.resize(small, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
    crop[:] = (bl * r["_soft"] + crop * (1 - r["_soft"])).astype(np.uint8)


def _hex_bgr(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return float(int(h[4:6], 16)), float(int(h[2:4], 16)), float(int(h[0:2], 16))


def _panel(f: np.ndarray, b: dict) -> None:
    """KHUNG lấp cả dải đáy / đỉnh: nền = phần HÌNH kề ngay bên (lật gương) nhoè mạnh + tối — không dùng điểm ảnh của
    chính dải nên chữ Trung không để lại vệt; mép sắc (khung có chủ ý), tuỳ chọn một nét kẻ mảnh màu shop."""
    H, W = f.shape[:2]
    y0, y1 = int(round(b["y0"] * H)), int(round(b["y1"] * H))
    h = y1 - y0
    if h < 4:
        return
    bottom = y1 >= H - 1 or (y0 + y1) / 2 > H / 2
    src = f[max(0, y0 - h):y0] if bottom else f[y1:min(H, y1 + h)]
    if src.shape[0] < 4:
        src = f
    src = cv2.flip(cv2.resize(src, (W, h), interpolation=cv2.INTER_AREA), 0)
    k = 8
    small = cv2.resize(src, (max(2, W // k), max(2, h // k)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), float(b.get("sigma", 0.045 * H)) / k)
    out = cv2.resize(small, (W, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    if b.get("tint"):
        t = float(b.get("tint_mix", 0.35))
        out = out * (1 - t) + np.array(_hex_bgr(b["tint"]), np.float32) * t
    out *= 1.0 - float(b.get("dim", 0.42))
    if b.get("line"):   # nét kẻ mảnh ở mép giáp hình
        row = 0 if bottom else h - max(1, round(H * 0.0016))
        th = max(1, round(H * 0.0016))
        a = float(b.get("line_alpha", 0.6))
        out[row:row + th] = out[row:row + th] * (1 - a) + np.array(_hex_bgr(b["line"]), np.float32) * a
    f[y0:y1] = np.clip(out, 0, 255).astype(np.uint8)


def _auto_panels(regs: list[dict], cfg: dict, H: int, fps: float, cuts: list[int]) -> tuple[list[dict], list[str], list[str]]:
    """Chữ Trung ngang ở dải đáy / đỉnh → một khung lấp cả dải (các ô đó không vá riêng nữa) — CHỈ KHI phần khung phải
    cắt (từ mép khung tới mép xa của chữ) ≤ `panel_max` (17% H). Ô nằm sâu quá ngưỡng bị loại khỏi khung dải (→ badge
    che, xem _groups); loại hết thì không có khung dải. Trả (dải, cảnh báo, ghi chú)."""
    out, warns, notes = [], [], []
    pmax = float(cfg.get("panel_max", PANEL_MAX))
    for side in ("bottom", "top"):
        if cfg.get(side, "panel") != "panel":
            continue
        mid = lambda r: (r["hug"][1] + r["hug"][3]) / 2   # noqa: E731
        rs = [r for r in regs if abs(r["angle"]) < 4 and r["method"] != "none"
              and (mid(r) > 0.78 * H if side == "bottom" else mid(r) < 0.22 * H)]
        if not rs:
            continue
        # phần khung phải cắt nếu ô này nằm trong dải; loại dần ô sâu nhất cho tới khi dải ≤ ngưỡng
        need = (lambda r: 1 - (r["hug"][1] - 10) / H) if side == "bottom" else (lambda r: (r["hug"][3] + 10) / H)
        deep = [r for r in rs if need(r) > pmax]
        rs = [r for r in rs if need(r) <= pmax]
        if deep:
            notes.append(f"khung dải {side}: {len(deep)} ô ({', '.join(r['id'] for r in deep[:6])}{'…' if len(deep) > 6 else ''}) "
                         f"nằm sâu — phủ dải sẽ cắt {max(need(r) for r in deep):.0%} chiều cao khung (> {pmax:.0%}) → dùng "
                         f"BADGE che ôm chữ")
        if not rs:
            continue
        if side == "bottom":
            band = {"y0": round(max(0, min(r["hug"][1] for r in rs) - 10) / H, 4), "y1": 1.0}
        else:
            band = {"y0": 0.0, "y1": round(min(H, max(r["hug"][3] for r in rs) + 10) / H, 4)}
        lost = []
        band.update(mode="panel", side=side, auto=True, **(cfg.get("panel") or {}))
        frames = sorted(set().union(*[r["on"] for r in rs if r["id"] not in lost]))
        spans = []   # khoảng có chữ Trung trong dải (khung) — gộp khe ngắn để khung không chớp tắt giữa hai dòng
        for i in frames:
            if spans and i - spans[-1][1] <= round(PANEL_GAP * fps):
                spans[-1][1] = i
            else:
                spans.append([i, i])
        if not band.get("hold"):
            # Mối CẮT CẢNH sát mép khoảng chữ Trung → khung bật / tắt ĐÚNG mối cắt (cắt cứng, không mờ): khung mờ vào sớm
            # 0,25s sẽ rơi lên cảnh TRƯỚC (đo 0379: khung dải hiện ở 3,78s đè lên badge hook, cảnh đổi ở 4,0s).
            near = round(0.35 * fps)
            band["spans"], band["hard_in"], band["hard_out"] = [], [], []
            for a, b in spans:
                cin = max((c for c in cuts if a - near <= c <= a + GROW), default=None)
                cout = min((c for c in cuts if b - GROW <= c <= b + near), default=None)
                t0 = round(cin / fps, 3) if cin is not None else round(max(0.0, a / fps - PANEL_LEAD), 3)
                t1 = round(cout / fps, 3) if cout is not None else round((b + 1) / fps + 0.08, 3)
                band["spans"].append([t0, t1])
                if cin is not None:
                    band["hard_in"].append(t0)
                if cout is not None:
                    band["hard_out"].append(t1)
        for r in rs:
            if r["id"] not in lost:
                r["t_span"] = (min(r["on"]) / fps, (max(r["on"]) + 1) / fps) if r["on"] else None
                r["on"], r["method"], r["mode"] = set(), "panel", f"khung dải {side}"
        out.append(band)
    return out, warns, notes


def _groups(regs: list[dict], cfg: dict, fps: float, cuts: list[int], W: int, H: int) -> list[dict]:
    """Gom các dòng chữ Trung NGANG không nằm trong khung dải thành NHÓM để lớp chữ Việt phủ MỘT badge cho cả nhóm:
    - `block` = các dòng hiện cùng lúc, xếp chồng / kề nhau (tiêu đề 2 dòng): một badge che cả khối;
    - `bar`   = các dòng (hoặc khối) nối tiếp nhau cùng một chỗ, cùng cỡ (phụ đề chạy suốt): badge giữ liền, chỉ đổi chữ;
    - `single`= một dòng / nhãn lẻ.
    Dòng xoay (sticker nghiêng) không gom — mỗi ô một badge xoay riêng (`caps.items[].over`)."""
    rs = [r for r in regs if abs(r["angle"]) < 4 and r["method"] in ("fill", "blur") and r["on"]]
    gap = float(cfg.get("lane_gap", PANEL_GAP))

    def merge(items, linked):
        parent = list(range(len(items)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        hit = set()
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if linked(items[i], items[j]):
                    hit.update((i, j))
                    parent[find(j)] = find(i)
        out = {}
        for i, it in enumerate(items):
            out.setdefault(find(i), []).append((it, i in hit))
        return list(out.values())

    def unit(ms, kind):
        return {"ms": ms, "kind": kind, "start": min(m["start"] for m in ms), "end": max(m["end"] for m in ms),
                "box": [min(m["hug"][0] for m in ms), min(m["hug"][1] for m in ms),
                        max(m["hug"][2] for m in ms), max(m["hug"][3] for m in ms)]}

    def stacked(a, b):   # hiện cùng lúc (theo mốc phân tích), chồng / kề nhau theo chiều dọc
        ot = min(a["end"], b["end"]) - max(a["start"], b["start"])
        (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a["hug"], b["hug"]
        return (ot >= 0.6 * min(a["end"] - a["start"], b["end"] - b["start"])
                and min(ax1, bx1) - max(ax0, bx0) > 0.3 * min(ax1 - ax0, bx1 - bx0)
                and max(ay0, by0) - min(ay1, by1) <= 0.7 * min(ay1 - ay0, by1 - by0))

    def chained(a, b):   # nối tiếp nhau (khe ≤ gap), cùng chỗ, cùng cỡ — so trên hộp của cả khối
        ot = min(a["end"], b["end"]) - max(a["start"], b["start"])
        (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a["box"], b["box"]
        ha, hb = ay1 - ay0, by1 - by0
        return (ot < 0.35 and -ot <= gap and min(ay1, by1) - max(ay0, by0) >= 0.6 * min(ha, hb)
                and 0.65 <= ha / max(1, hb) <= 1.55 and abs((ax0 + ax1) - (bx0 + bx1)) / 2 <= 0.2 * W)

    units = [unit([m for m, _ in grp], "block" if len(grp) > 1 else "single") for grp in merge(rs, stacked)]
    near = round(0.35 * fps)
    out = []
    for grp in sorted(merge(units, chained), key=lambda g: min(u["start"] for u, _ in g)):
        us = [u for u, _ in grp]
        ms = sorted((m for u in us for m in u["ms"]), key=lambda m: m["start"])
        a, b = min(min(m["on"]) for m in ms), max(max(m["on"]) for m in ms)
        cin = max((c for c in cuts if a - near <= c <= a + GROW), default=None)
        cout = min((c for c in cuts if b - GROW <= c <= b + near), default=None)
        box = unit(ms, "")["box"]
        g = {"id": f"G{len(out) + 1}", "kind": "bar" if len(us) > 1 else us[0]["kind"],
             "members": [m["id"] for m in ms],
             "box": [max(0, box[0] - 4), max(0, box[1] - 4), min(W, box[2] + 4), min(H, box[3] + 4)],
             "t0": round(cin / fps if cin is not None else a / fps, 3),
             "t1": round(cout / fps if cout is not None else (b + 1) / fps, 3),
             "hard_in": bool(cin is not None or a <= 1), "hard_out": cout is not None}
        g["area_pct"] = round((g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1]) / (W * H), 4)
        for m in ms:
            m["group"] = g["id"]
        out.append(g)
    return out


def _band_k(b: dict, t: float) -> float:
    """Độ hiện của dải lúc t (0..1): theo `spans` (khung chỉ hiện khi có chữ Trung) hoặc start/end khai tay."""
    spans = b.get("spans")
    if spans is None:
        return 1.0 if b.get("start", 0.0) <= t <= b.get("end", 1e9) else 0.0
    k = 0.0
    for a, z in spans:
        cut_out = z in b.get("hard_out", ())
        if a - 0.001 <= t < (z - 0.001 if cut_out else z + PANEL_FADE):
            # vào: đục 100% trước khi chữ Trung hiện (bật cứng nếu đúng mối cắt cảnh / đầu video)
            vin = 1.0 if (a <= 0.001 or a in b.get("hard_in", ())) else min(1.0, (t - a) / PANEL_FADE)
            vout = 1.0 if cut_out else min(1.0, max(0.0, (z + PANEL_FADE - t) / PANEL_FADE))   # mờ ra SAU khi chữ Trung tắt
            k = max(k, vin * vout)
    return k


def _band(f: np.ndarray, b: dict) -> None:
    """Một dải ngang: `panel` = khung lấp (mép sắc) · `blur` / `dim` = làm mờ / tối mép mềm."""
    H, W = f.shape[:2]
    if b.get("mode") == "panel":
        _panel(f, b)
        return
    if "_soft" not in b:
        y0, y1 = int(b.get("y0", 0.86) * H), int(b.get("y1", 1.0) * H)
        fe = max(4, int(b.get("feather", 0.035) * H))
        rows = np.arange(H, dtype=np.float32)
        up = np.clip((rows - (y0 - fe)) / (2 * fe), 0, 1)                       # mép trên mềm
        dn = np.clip(((y1 + fe) - rows) / (2 * fe), 0, 1) if y1 < H else np.ones(H, np.float32)
        m = (up * up * (3 - 2 * up)) * (dn * dn * (3 - 2 * dn))                 # smoothstep
        a0, a1 = max(0, y0 - fe), min(H, y1 + fe)
        b["_rows"] = (a0, a1)
        b["_soft"] = m[a0:a1].reshape(-1, 1, 1)
    a0, a1 = b["_rows"]
    crop = f[a0:a1]
    mode = b.get("mode", "blur")
    out = crop.astype(np.float32)
    if mode == "blur":
        k = 4
        small = cv2.resize(crop, (max(2, W // k), max(2, crop.shape[0] // k)), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), float(b.get("sigma", 0.022 * H)) / k)
        out = cv2.resize(small, (W, crop.shape[0]), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    out *= 1.0 - float(b.get("dim", 0.18 if mode == "blur" else 0.35))
    crop[:] = (out * b["_soft"] + crop * (1 - b["_soft"])).astype(np.uint8)


def build(job_dir: Path, edl: dict, meta: dict, force: bool = False) -> Path | None:
    """Tạo `source-clean.mp4` (cùng cỡ, fps, số khung, kèm tiếng gốc) — cache theo cấu hình + nguồn. Không bật → None."""
    if not enabled(edl):
        return None
    src = job_dir / meta["source"]
    W, H, fps = meta["width"], meta["height"], meta["fps"]
    regs = regions(edl, meta)
    bands = [dict(b) for b in _cfg(edl).get("bands", [])]
    st = src.stat()
    cfg = dict(_cfg(edl))
    cfg["panel"] = {**(shop_caps(edl.get("shop")).get("panel") or {}), **(cfg.get("panel") or {})}   # màu khung dải theo shop
    key = hashlib.sha1(json.dumps([regs, bands, {k: cfg.get(k) for k in ("bottom", "top", "panel", "panel_max",
                                                                         "lane_gap", "cover_max")},
                                   st.st_size, st.st_mtime_ns, VERSION], sort_keys=True,
                                  ensure_ascii=False).encode()).hexdigest()[:16]
    out, rep_path = job_dir / OUT, job_dir / "clean.json"
    if not force and out.exists() and rep_path.exists():
        if json.loads(rep_path.read_text(encoding="utf-8")).get("key") == key:
            return out
    n, cuts = _scan(src, regs, fps)
    warns = _decide(regs, fps, n, W, H, cuts)
    _resolve_overlaps(regs, fps)
    auto, w2, notes = _auto_panels(regs, cfg, H, fps, cuts)
    bands += auto
    covered = {r["id"] for r in regs if r["method"] == "panel"}   # ô đã nằm trong khung dải: khỏi báo "ô tĩnh"
    warns = [w for w in warns if w.split(" ", 1)[0] not in covered] + w2
    groups = _groups(regs, cfg, fps, cuts, W, H)
    big = float(cfg.get("cover_max", COVER_MAX))
    for g in groups:   # chữ Trung phủ quá nhiều khung → badge che cũng không tinh tế nổi
        if g["area_pct"] > big:
            warns.append(f"nhóm {g['id']} ({', '.join(g['members'])}) {g['t0']:.1f}–{g['t1']:.1f}s phủ {g['area_pct']:.0%} khung "
                         f"(> {big:.0%}) — badge che sẽ quá to: cân nhắc cắt bỏ đoạn / đổi cảnh / thẻ phủ khung, hỏi Sếp")
    tmp = job_dir / "source-clean.tmp.mp4"
    cmd = [config.FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{fps}",
           "-i", "-", "-i", str(src), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "13", "-pix_fmt", "yuv420p", *media.BT709_OUT, "-c:a", "copy", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    cap = cv2.VideoCapture(str(src))
    i = 0
    try:
        while True:
            ok, f = cap.read()
            if not ok:
                break
            if f.shape[1] != W or f.shape[0] != H:
                f = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA)
            t = i / fps
            for r in regs:
                if i in r["on"]:
                    if i in r.get("pre", ()):
                        if "_held" in r:
                            _hold(f, r)
                        else:   # không có khung sạch cùng cảnh (chữ vào đúng mối cắt) → nhoè vùng rộng
                            _blur_wide(f, r, 2.2)
                    elif r["method"] == "fill":
                        _fill(f, r, i)
                    else:
                        _blur(f, r)
                        back = i - max(r["pre"]) if r.get("pre") and "_held" in r else 9
                        if back <= 2:   # 2 khung trả dần hình thật quanh badge → không giật
                            _hold(f, r, 1.0 - back / 3)
            for r in regs:   # giữ hình sạch của khung ngay trước lúc chữ bật vào (sau khi các ô khác đã được xoá)
                if r.get("hold_at") == i:
                    r["_hz"] = _hold_zone(r, W, H)
                    x0, y0, x1, y1 = r["_hz"]
                    r["_held"] = f[y0:y1, x0:x1].astype(np.float32)
            for b in bands:
                k = _band_k(b, t)
                if k >= 0.999:
                    _band(f, b)
                elif k > 0.001:   # đang mờ vào / ra: trộn với hình gốc (lúc này chưa / hết chữ Trung)
                    y0, y1 = int(b["y0"] * H), int(round(b["y1"] * H))
                    keep = f[y0:y1].astype(np.float32)
                    _band(f, b)
                    f[y0:y1] = (f[y0:y1] * k + keep * (1 - k)).astype(np.uint8)
            proc.stdin.write(f.tobytes())
            i += 1
    finally:
        cap.release()
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0:
            raise RuntimeError(f"Ghi {OUT} lỗi: {err[-600:]}")
    tmp.replace(out)
    rep = {"key": key, "frames": n, "cuts": [round(c / fps, 3) for c in cuts], "warnings": warns, "notes": notes,
           "groups": groups, "bands": len(bands),
           "panels": [{"side": b.get("side") or ("bottom" if b["y1"] >= 0.99 else "top" if b["y0"] <= 0.01 else "mid"),
                       "y0": int(round(b["y0"] * H)), "y1": int(round(b["y1"] * H)), "spans": b.get("spans")}
                      for b in bands if b.get("mode") == "panel"], "regions": [
        {"id": r["id"], "zh": r["zh"], "method": r["method"], "mode": r["mode"], "seen_ratio": r["seen_ratio"],
         "box": r["hug"], "angle": r["angle"],
         "rect": [round(r["rect"][0][0], 1), round(r["rect"][0][1], 1), round(r["rect"][1][0], 1),
                  round(r["rect"][1][1], 1), round(r["rect"][2], 2)],
         "t0": round(r["t_span"][0], 3) if r.get("t_span") else round(min(r["on"]) / fps, 3) if r["on"] else None,
         "t1": round(r["t_span"][1], 3) if r.get("t_span") else round((max(r["on"]) + 1) / fps, 3) if r["on"] else None,
         "ts": round((min(set(r["on"]) - set(r.get("pre", ()))) / fps), 3) if set(r["on"]) - set(r.get("pre", ())) else None,
         "pre": len(r.get("pre", ())), "held": r.get("hold_at") is not None, "group": r.get("group")}
        for r in regs]}
    rep_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  xoá chữ Trung: {len(regs)} vùng ({sum(r['method'] == 'panel' for r in regs)} nằm trong khung dải, "
          f"{sum(r['method'] == 'fill' for r in regs)} nội suy nền, {sum(r['method'] == 'blur' for r in regs)} nhoè) "
          f"+ {len(bands)} dải → {OUT}")
    for g in groups:
        print(f"    nhóm {g['id']} [{g['kind']}] {g['t0']:.2f}–{g['t1']:.2f}s · ô {g['box']} ({g['area_pct']:.0%} khung) · "
              f"{', '.join(g['members'])}")
    for w in notes:
        print(f"  ℹ {w}")
    for w in warns:
        print(f"  ⚠ {w}")
    return out


def report(job_dir: Path) -> dict | None:
    p = job_dir / "clean.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
