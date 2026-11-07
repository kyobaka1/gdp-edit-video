"""Dựng video từ jobs/<id>/edit.json (skill gdp-video-edit).

Hình: Python đọc từng nguồn qua ffmpeg (rawvideo), đặt khung bằng warpAffine (zoom dưới pixel, mượt hơn crop ffmpeg),
chuyển cảnh + chữ động + logo ghép bằng numpy, đẩy khung thô vào ffmpeg mã hoá H.264. Tiếng: ghép các đoạn lời bằng
numpy (vuốt 8ms chống tiếng tách), lọc + nén giọng, nhạc (nếu có), rồi chuẩn độ to cả bản −14 LUFS
(render._normalize_loudness, dùng chung với luồng Việt hoá).
"""

import json
import subprocess
import time
import wave
from pathlib import Path

import cv2
import numpy as np

from studio import config, media
from studio.edit import project
from studio.edit.kinetic import Kinetic
from studio.render import _normalize_loudness, measure_lufs

SR = 48000
# Vùng an toàn TikTok 9:16 (tỉ lệ khung): trên = thanh LIVE/tab, phải = cột tim/bình luận, dưới = tên + mô tả.
# Mẫu để chữ "TỐT" lọt dưới nút tim (05/11) → chữ phải nằm trọn trong vùng này.
SAFE = (0.06, 0.12, 0.84, 0.76)
PLACES = [("center", 0.46), ("left", 0.07), ("right", 0.83)]   # "giữa" = giữa vùng an toàn (lệch trái vì cột nút phải)
Y_OPTS = [0.47, 0.40, 0.56]
DIP_OUT, DIP_IN, WIPE, FLASH = 0.18, 0.12, 0.15, 1.5   # giây (FLASH: số khung mỗi bên)


# ───────────────────────────── nguồn hình ─────────────────────────────
class Reader:
    """Đọc khung liên tục từ một nguồn, bắt đầu ở giây s0, đổi về fps đầu ra."""

    def __init__(self, path: Path, s0: float, dur: float, fps: float, w: int, h: int):
        self.w, self.h, self.last = w, h, None
        self.p = subprocess.Popen([config.FFMPEG, "-v", "error", "-ss", f"{max(0.0, s0):.3f}", "-i", str(path),
                                   "-t", f"{dur + 0.25:.3f}", "-vf", f"fps={fps}", "-f", "rawvideo",
                                   "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self) -> np.ndarray:
        n = self.w * self.h * 3
        buf = self.p.stdout.read(n)
        if len(buf) == n:
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        elif self.last is None:
            self.last = np.zeros((self.h, self.w, 3), np.uint8)
        return self.last

    def close(self) -> None:
        self.p.stdout.close()
        self.p.kill()
        self.p.wait()


def grab(path: Path, s: float, w: int, h: int) -> np.ndarray:
    r = Reader(path, s, 0.1, 30, w, h)
    try:
        return r.read().copy()
    finally:
        r.close()


def place(frame: np.ndarray, W: int, H: int, zoom: float, focus, fit: str, interp: int) -> np.ndarray:
    """Đặt khung nguồn vào khung ra: fill (cắt cho kín) hoặc fit (vừa khung, nền nhoè). zoom ≥1 = cắt chặt hơn,
    focus = điểm nguồn (0..1) đưa về giữa khung, tự giới hạn để không lộ viền."""
    h, w = frame.shape[:2]
    fx, fy = focus

    def warp(s: float, cx: float, cy: float, clamp: bool) -> np.ndarray:
        tx, ty = W / 2 - s * cx * w, H / 2 - s * cy * h
        if clamp:
            tx = min(0.0, max(W - s * w, tx))
            ty = min(0.0, max(H - s * h, ty))
        M = np.float32([[s, 0, tx], [0, s, ty]])
        return cv2.warpAffine(frame, M, (W, H), flags=interp, borderMode=cv2.BORDER_REPLICATE)

    if fit == "fit":
        bg = warp(max(W / w, H / h), 0.5, 0.5, True)
        bg = cv2.GaussianBlur(cv2.resize(bg, (W // 8, H // 8)), (0, 0), 3)
        bg = (cv2.resize(bg, (W, H)) * 0.55).astype(np.uint8)
        fg = warp(min(W / w, H / h) * zoom, fx, fy, False)
        s = min(W / w, H / h) * zoom
        x0, y0 = int(round(W / 2 - s * fx * w)), int(round(H / 2 - s * fy * h))
        x1, y1 = int(round(x0 + s * w)), int(round(y0 + s * h))
        out = bg.copy()
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        out[Y0:Y1, X0:X1] = fg[Y0:Y1, X0:X1]
        return out
    return warp(max(W / w, H / h) * zoom, fx, fy, True)


# Dò mặt: YuNet (cv2.FaceDetectorYN, OpenCV 5 đã bỏ Haar CascadeClassifier). TUỲ CHỌN: Sếp chọn KHÔNG tải file mô
# hình (05/11) → không có file thì bỏ qua, né mặt bằng soát mắt ảnh qa_*.jpg + ép pos/y trong cut.py. Có đặt file
# face_detection_yunet_2023mar.onnx (opencv_zoo) vào assets/models/ thì chữ tự né mặt.
FACE_MODEL = config.ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
_YUNET = None


def face_ready() -> bool:
    return FACE_MODEL.exists()


def faces(img: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Mặt người → [(x, y, w, h)] theo toạ độ ảnh vào (chạy trên ảnh thu về rộng 480 cho nhanh)."""
    global _YUNET
    if not face_ready():
        return []
    k = 480 / img.shape[1]
    small = cv2.resize(img, None, fx=k, fy=k)
    h, w = small.shape[:2]
    if _YUNET is None:
        _YUNET = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (w, h), 0.7, 0.3, 50)
    _YUNET.setInputSize((w, h))
    _, det = _YUNET.detect(small)
    if det is None:
        return []
    return [tuple(int(round(v / k)) for v in d[:4]) for d in det if d[2] * d[3] > (w * 0.04) ** 2]


# ───────────────────────────── trục cảnh ─────────────────────────────
def zoom_at(shot: dict, t: float) -> float:
    a, b = shot["za"], shot["zb"]
    p = 0.0 if b <= a else min(1.0, max(0.0, (t - a) / (b - a)))
    return shot["z0"] + (shot["z1"] - shot["z0"]) * p


def shots(e: dict, src: dict) -> tuple[list[dict], list[tuple[float, str]]]:
    T = e["duration"]
    cuts = {0.0, T}
    for x in e["pieces"] + e["covers"] + e["cards"]:
        cuts |= {x["t0"], x["t1"]}
    cuts = sorted(c for c in cuts if 0 <= c <= T)
    groups = {}
    for p in e["pieces"]:
        g = groups.setdefault(p["group"], [p["t0"], p["t1"]])
        g[0], g[1] = min(g[0], p["t0"]), max(g[1], p["t1"])
    out = []
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 1e-3:
            continue
        m = (a + b) / 2
        cards = [k for k, c in enumerate(e["cards"]) if c["t0"] <= m < c["t1"]]
        covers = [k for k, c in enumerate(e["covers"]) if c["t0"] <= m < c["t1"]]
        glass = bool(cards) and e["cards"][cards[-1]].get("bg") == "glass"
        if cards and not glass:
            s = {"kind": "card", "ref": f"card{cards[-1]}", "bg": e["cards"][cards[-1]]["bg"]}
        elif covers:
            c = e["covers"][covers[-1]]
            s = {"kind": "cover", "ref": f"cover{covers[-1]}", "src": c["src"], "s0": c["src_in"] + (a - c["t0"]) * c["speed"],
                 "speed": c["speed"], "fit": c["fit"], "focus": c["focus"],
                 "z0": 1.0, "z1": 1.0 + c["push"], "za": c["t0"], "zb": c["t1"]}
        else:
            p = next(p for p in e["pieces"] if p["t0"] <= m < p["t1"] + 1e-6)
            if not src[p["src"]].get("has_video"):
                s = {"kind": "card", "ref": "black", "bg": "black"}
            else:
                g0, g1 = groups[p["group"]]
                s = {"kind": "piece", "ref": f"g{p['group']}", "src": p["src"], "s0": p["in"] + (a - p["t0"]), "speed": 1.0,
                     "fit": "fill", "focus": p.get("focus") or [0.5, 0.42], "group": p["group"],
                     "z0": p["zoom"], "z1": p["zoom"] * (1 + (p.get("push") or 0)), "za": g0, "zb": g1}
        if glass and s["kind"] != "card":   # kính mờ = hình bên dưới vẫn chạy, nhoè + tối (ref riêng → tách đoạn)
            s["glass"], s["ref"] = True, s["ref"] + f"-glass{cards[-1]}"
        s.update(t0=round(a, 4), t1=round(b, 4))
        prev = out[-1] if out else None
        if (prev and prev["ref"] == s["ref"] and prev["kind"] != "card" and
                abs(prev["s0"] + (prev["t1"] - prev["t0"]) * prev["speed"] - s["s0"]) < 0.02):
            prev["t1"] = s["t1"]
        elif prev and prev["kind"] == "card" and s["kind"] == "card" and prev["ref"] == s["ref"]:
            prev["t1"] = s["t1"]
        else:
            out.append(s)
    trans = []
    for c in e["covers"]:
        trans += [(c["t0"], c["trans"]), (c["t1"], c["trans_out"])]
    for c in e["cards"]:
        trans += [(c["t0"], c["trans"]), (c["t1"], c["trans"])]
    trans = sorted({(round(t, 4), k) for t, k in trans if k != "cut" and 0 < t < T})
    return out, trans


def still(job: Path, src: dict, shot: dict, t: float, W: int, H: int) -> np.ndarray:
    if shot["kind"] == "card":
        return np.zeros((H, W, 3), np.uint8)
    s = src[shot["src"]]
    f = grab(job / s["file"], shot["s0"] + (t - shot["t0"]) * shot["speed"], s["width"], s["height"])
    return place(f, W, H, zoom_at(shot, t), shot["focus"], shot["fit"], cv2.INTER_LINEAR)


def shot_at(sh: list[dict], t: float) -> dict:
    return next((s for s in sh if s["t0"] <= t < s["t1"]), sh[-1])


def focus_faces(job: Path, e: dict, src: dict) -> None:
    """Đoạn người nói chưa ép focus → lấy mặt ở giữa đoạn làm tâm khung (mặt ở 1/3 trên) khi zoom chặt."""
    done = {}
    for p in e["pieces"]:
        s = src[p["src"]]
        if p.get("focus") or not s.get("has_video"):
            continue
        if p["group"] not in done:
            f = grab(job / s["file"], (p["in"] + p["out"]) / 2, s["width"], s["height"])
            fs = sorted(faces(f), key=lambda r: -r[2] * r[3])
            done[p["group"]] = ([round((fs[0][0] + fs[0][2] / 2) / s["width"], 3),
                                 round(min(0.6, (fs[0][1] + fs[0][3] / 2) / s["height"] + 0.12), 3)] if fs else [0.5, 0.42])
        p["focus"] = done[p["group"]]


# ───────────────────────────── chữ động ─────────────────────────────
def _cap_cfg(e: dict) -> tuple[list, list, float]:
    """Vị trí đặt chữ động: mặc định cinematic (giữa ~47%) · phong cách đổi (vd giải thích: 1 dòng nhỏ ~74%)."""
    c = (e.get("style_cfg") or {}).get("captions") or {}
    places = [pl for pl in PLACES if pl[0] in c["places"]] if c.get("places") else PLACES
    return places or PLACES, c.get("y_opts") or Y_OPTS, float(c.get("y", 0.47))


def _js_blocks(e: dict) -> list[dict]:
    y_def = _cap_cfg(e)[2]
    out = []
    for b in e["captions"]:
        lines = [{"role": ln["role"], "italic": ln.get("italic", False), "accent": ln.get("accent", False),
                  **({"morph_at": ln["morph_at"]} if ln.get("morph_at") is not None else {}),
                  "words": [{"text": w["text"], "t": w["t"]} for w in ln["words"]]} for ln in b["lines"]]
        out.append({"id": b["id"], "end": b["end"], "exit": b["exit"], "card": b["card"], "lines": lines,
                    **({"stagger": b["stagger"]} if b.get("stagger") else {}),
                    "align": "center", "x": 0.46, "y": b.get("y") or y_def})
    return out


def _rect(mode: str, x: float, y: float, w: int, h: int, W: int, H: int) -> tuple[int, int, int, int]:
    x0 = x * W - (w / 2 if mode == "center" else w if mode == "right" else 0)
    return int(x0), int(y * H - h / 2), w, h


def _overlap(r, boxes) -> float:
    x, y, w, h = r
    tot = 0
    for bx, by, bw, bh in boxes:
        tot += max(0, min(x + w, bx + bw) - max(x, bx)) * max(0, min(y + h, by + bh) - max(y, by))
    return tot / max(1, w * h)


def _outside(r, W, H) -> float:
    x, y, w, h = r
    sx0, sy0, sx1, sy1 = SAFE[0] * W, SAFE[1] * H, SAFE[2] * W, SAFE[3] * H
    inside = max(0, min(x + w, sx1) - max(x, sx0)) * max(0, min(y + h, sy1) - max(y, sy0))
    return 1 - inside / max(1, w * h)


def plan_captions(job: Path, e: dict, src: dict, sh: list[dict], kin: Kinetic, W: int, H: int,
                  avoid: list | None = None) -> list[dict]:
    """Chọn chỗ đặt từng khối: né mặt (OpenCV) + nằm trong vùng an toàn TikTok; màn chữ luôn ở giữa.
    avoid = [(t0, t1, (x, y, w, h))] vùng đồ hoạ đang hiện mà chữ động vẫn chạy (tiêu đề ghim) → khối chữ né ra."""
    js = _js_blocks(e)
    boxes = kin.load(js)
    places, y_opts, y_def = _cap_cfg(e)
    report = []
    for b, jb, bx in zip(e["captions"], js, boxes):
        times = [b["first"] + 0.05, (b["first"] + b["end"]) / 2, max(b["first"] + 0.05, b["end"] - 0.05)]
        fb = []
        gb = [r for a0, a1, r in (avoid or []) if a0 < b["end"] and a1 > b["first"]]
        if not b["card"]:
            for t in times:
                s = shot_at(sh, t)
                if s["kind"] != "card":
                    fb += faces(still(job, src, s, t, W, H))
        w, h = bx["w"], bx["h"]
        if b["card"]:
            cands = [("center", 0.5, b.get("y") or 0.47)]
        elif b["pos"] != "auto":
            x = dict(PLACES)[b["pos"]]
            cands = [(b["pos"], x, b.get("y") or yy) for yy in ([b["y"]] if b.get("y") else y_opts)]
        else:
            cands = [(m, x, b.get("y") or yy) for m, x in places for yy in ([b["y"]] if b.get("y") else y_opts)]

        def score(c):
            r = _rect(c[0], c[1], c[2], w, h, W, H)
            return (10 * _overlap(r, fb) + 10 * _outside(r, W, H) + 10 * _overlap(r, gb) + (0.15 if c[0] != "center" else 0)
                    + abs(c[2] - y_def) * 1.0)
        m, x, y = min(cands, key=score)
        jb.update(align=m, x=x, y=y)
        r = _rect(m, x, y, w, h, W, H)
        if gb:
            cands_y = sorted({c[2] for c in cands})
            if all(_overlap(_rect(m, x, yy, w, h, W, H), gb) > 0.02 for yy in cands_y) and not b.get("y"):
                for yy in (0.62, 0.66, 0.70):   # mọi cao độ chuẩn đều chạm tiêu đề ghim → hạ thấp dần
                    if _overlap(_rect(m, x, yy, w, h, W, H), gb) <= 0.02 and _outside(_rect(m, x, yy, w, h, W, H), W, H) <= 0.01:
                        y = yy
                        jb.update(y=y)
                        r = _rect(m, x, y, w, h, W, H)
                        break
        report.append({"id": b["id"], "pos": m, "x": x, "y": y, "faces": fb, "face_overlap": round(_overlap(r, fb), 3),
                       "graphic_overlap": round(_overlap(r, gb), 3),
                       "outside_safe": round(_outside(r, W, H), 3), "markup": b["markup"]})
    final = kin.load(js)   # đo lại sau khi đặt chỗ → khung thật cho QA
    for rp, bx in zip(report, final):
        r = (bx["x"], bx["y"], bx["w"], bx["h"])
        rp.update(rect=list(r), face_overlap=round(_overlap(r, rp["faces"]), 3), outside_safe=round(_outside(r, W, H), 3))
    return report


# ───────────────────────────── tiếng ─────────────────────────────
def read_audio(path: Path, s0: float, dur: float) -> np.ndarray:
    out = subprocess.run([config.FFMPEG, "-v", "error", "-ss", f"{max(0.0, s0):.3f}", "-t", f"{dur:.3f}", "-i", str(path),
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(out, np.float32).copy()


def _fit(a: np.ndarray, n: int) -> np.ndarray:
    return a[:n] if len(a) >= n else np.concatenate([a, np.zeros(n - len(a), np.float32)])


def _fade(a: np.ndarray, ms: float) -> np.ndarray:
    k = min(len(a) // 2, int(SR * ms / 1000))
    if k > 1:
        r = np.linspace(0, 1, k, dtype=np.float32)
        a[:k] *= r
        a[-k:] *= r[::-1]
    return a


def write_wav(path: Path, a: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def build_audio(job: Path, e: dict, src: dict, work: Path, sfx: list | None = None) -> Path:
    T = e["duration"]
    n = int(round(T * SR))
    voice = np.zeros(n, np.float32)
    for p in e["pieces"]:
        k0, k1 = int(round(p["t0"] * SR)), int(round(p["t1"] * SR))
        seg = _fade(_fit(read_audio(job / src[p["src"]]["file"], p["in"], p["out"] - p["in"]), k1 - k0), 8)
        voice[k0:k1] += seg
    raw = work / "voice_raw.wav"
    write_wav(raw, voice)
    cfg = e["audio"]
    vo = work / "voice.wav"
    if cfg.get("clean", True):  # lọc ù + nén giọng (mẫu: dải động rất hẹp, LRA 1,8)
        media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(raw), "-af",
                   "highpass=f=75,acompressor=threshold=-22dB:ratio=3:attack=6:release=120:makeup=2,"
                   "alimiter=limit=0.89:level=0", "-ar", str(SR), "-ac", "1", str(vo)])
    else:
        raw.replace(vo)
    mix = read_audio(vo, 0, T + 0.5)
    mix = _fit(mix, n)
    for c in e["covers"]:   # tiếng gốc của cảnh minh hoạ (mặc định tắt)
        if c.get("ambient"):
            k0, k1 = int(round(c["t0"] * SR)), int(round(c["t1"] * SR))
            amb = _fade(_fit(read_audio(job / src[c["src"]]["file"], c["src_in"], c["t1"] - c["t0"]), k1 - k0), 40)
            mix[k0:k1] += amb * float(c["ambient"])
    if cfg.get("music"):
        mp = Path(cfg["music"])
        mp = mp if mp.is_absolute() else job / mp
        mus = read_audio(mp, 0, T + 1)
        if len(mus):
            mus = np.tile(mus, int(np.ceil(n / len(mus))))[:n]
            tmp = work / "music_raw.wav"
            write_wav(tmp, mus)
            now = measure_lufs(tmp) or -20.0
            mus *= 10 ** ((float(cfg.get("music_lufs", -30)) - now) / 20)
            k = int(SR * 1.0)
            mus[:k] *= np.linspace(0, 1, k, dtype=np.float32)
            mus[-k:] *= np.linspace(1, 0, k, dtype=np.float32)
            mix += mus
    for f, gain_db, at in sfx or []:   # tiếng hiệu ứng của scene (giấy vút, kính ting…) — đỉnh gain_db dBFS, dưới giọng
        s = read_audio(Path(f), 0, 3.0)
        if len(s):
            s = s / (np.abs(s).max() + 1e-9) * 10 ** (float(gain_db) / 20)
            k0 = int(round(at * SR))
            k1 = min(n, k0 + len(s))
            if k1 > k0:
                mix[k0:k1] += s[:k1 - k0]
    out = work / "mix.wav"
    write_wav(out, mix)
    return out


# ───────────────────────────── ghép khung ─────────────────────────────
def _blend(dst: np.ndarray, png: np.ndarray, x: int, y: int) -> None:
    h, w = png.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    p = png[y0 - y:y1 - y, x0 - x:x1 - x]
    a = p[:, :, 3:4].astype(np.float32) / 255.0
    roi = dst[y0:y1, x0:x1]
    dst[y0:y1, x0:x1] = (roi * (1 - a) + p[:, :, :3] * a).astype(np.uint8)


def _bleach(f: np.ndarray, a: float) -> np.ndarray:
    g = cv2.cvtColor(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR).astype(np.float32)
    g = g + (255 - g) * 0.45
    return (f.astype(np.float32) * (1 - a) + g * a).astype(np.uint8)


GRADES = {   # vig = độ tối góc · sat = độ bão hoà (1 = giữ) · warm = ấm (+) · gamma · white = trắng tối đa
    "cinematic": {"vig": 0.28, "sat": 1.0, "warm": 0.0, "gamma": 1.06, "white": 0.94},   # mẫu vlog 05/11
    "toi-vang": {"vig": 0.42, "sat": 0.72, "warm": 0.05, "gamma": 1.12, "white": 0.90},  # mẫu m2: hạ bão hoà, tối 4 góc
    "sach": {"vig": 0.12, "sat": 1.02, "warm": 0.0, "gamma": 1.0, "white": 0.97},       # mẫu Blue 1: sáng, sạch, nhẹ viền
}


def _grade(W: int, H: int, kind: str = "cinematic"):
    """Chỉnh màu theo phong cách (GRADES): tối viền + nén vùng sáng (+ hạ bão hoà / ấm cho "toi-vang").
    Áp cho người nói + cảnh minh hoạ, không áp màn chữ. Trả hàm f(frame) → frame."""
    g = GRADES.get(kind) or GRADES["cinematic"]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    vig = (1 - g["vig"] * np.clip((r - 0.35) / 0.65, 0, 1) ** 1.6)[..., None].astype(np.float32)
    x = np.arange(256, dtype=np.float32) / 255
    lut = np.clip(255 * (g["white"] * x ** g["gamma"] + 0.02 * np.sin(np.pi * x)), 0, 255).astype(np.uint8)
    tint = np.array([1 - g["warm"], 1.0, 1 + g["warm"] * 0.8], np.float32)   # BGR: ấm = bớt xanh dương, thêm đỏ
    plain = g["sat"] == 1.0 and not g["warm"]

    def apply(f: np.ndarray) -> np.ndarray:
        o = cv2.LUT(f, lut).astype(np.float32)
        if plain:
            return (o * vig).astype(np.uint8)
        if g["sat"] != 1.0:
            gray = o.mean(axis=2, keepdims=True)
            o = gray + (o - gray) * g["sat"]
        if g["warm"]:
            o *= tint
        return np.clip(o * vig, 0, 255).astype(np.uint8)
    return apply


def _glass(f: np.ndarray, k: float = 1.0) -> np.ndarray:
    """Màn chữ nền KÍNH MỜ (mẫu Blue 1 "thì đây là 4 điều"): hình đang chạy nhoè mạnh + tối, chữ đứng giữa.
    k = mức kính 0..1 (vào/ra nhoè dần 0,2s thay cho tối dần)."""
    h, w = f.shape[:2]
    small = cv2.resize(f, (max(8, w // 8), max(8, h // 8)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    b = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    g = np.clip(b * 0.52 + 6, 0, 255)
    if k >= 1:
        return g.astype(np.uint8)
    return (f.astype(np.float32) * (1 - k) + g * k).astype(np.uint8)


def _logo(e: dict, W: int, H: int):
    cfg = e.get("logo")
    if not cfg:
        return None
    from PIL import Image
    from studio.logo import _logo_file
    im = Image.open(_logo_file(cfg["shop"], cfg.get("file_key", "primary"))).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    im = im.crop(bb) if bb else im
    lw = round(W * cfg.get("width_pct", 0.14))
    im = im.resize((lw, round(im.height * lw / im.width)), Image.LANCZOS)
    arr = cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGRA)
    # dưới thanh LIVE/tab của TikTok (vùng an toàn trên = 12% chiều cao)
    x = round(W * 0.05) if cfg.get("corner", "top-left").endswith("left") else W - round(W * 0.05) - lw
    return arr, x, round(H * SAFE[1])


def graphic_box(info: dict, W: int, H: int) -> tuple[int, int, int, int]:
    """Vị trí clip đồ hoạ (đã cắt sát bbox) trên khung ra W×H: (x, y, w, h) — w, h chẵn."""
    cw, ch = info["canvas"]
    x, y, w, h = info["bbox"]
    k = W / cw
    return round(x * k), round(y * H / ch), max(2, round(w * k)) // 2 * 2, max(2, round(h * H / ch)) // 2 * 2


class GraphicReader:
    """Đồ hoạ phủ khung (thư viện motion, `c.graphic`) → khung BGRA đúng cỡ ra, đọc tuần tự theo thời gian."""

    def __init__(self, info: dict, t0: float, W: int, H: int):
        self.x, self.y, self.w, self.h = graphic_box(info, W, H)
        self.t0, self.fps, self.n = t0, info["fps"], info["frames"]
        self.p = subprocess.Popen([config.FFMPEG, "-v", "error", "-i", info["mov"], "-vf",
                                   f"scale={self.w}:{self.h}:flags=bicubic,format=bgra", "-f", "rawvideo", "-"],
                                  stdout=subprocess.PIPE)
        self.i, self.cur = -1, None

    def at(self, t: float) -> np.ndarray | None:
        want = min(self.n - 1, max(0, int(round((t - self.t0) * self.fps))))
        while self.i < want:
            buf = self.p.stdout.read(self.w * self.h * 4)
            if len(buf) < self.w * self.h * 4:
                break
            self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 4)
            self.i += 1
        return self.cur

    def close(self):
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait()


# ───────────────────────────── chữ sau người ─────────────────────────────
# Tách người: Robust Video Matting (github PeterL1n/RobustVideoMatting v1.0.0, GPL-3.0 — Sếp duyệt tải 05/11, chạy máy,
# miễn phí). ONNX trên CPU ~40ms/khung ở 540×960; có trạng thái hồi quy (khung sau dựa khung trước → viền tóc ổn định).
# Không có file → chữ luôn nằm trước người.
MATTE_MODEL = config.ROOT / "assets" / "models" / "rvm_mobilenetv3_fp32.onnx"
MATTE_LONG = 960   # cạnh dài khung đưa vào mô hình (mô hình tự thu 0,5 bên trong)


def matte_ready() -> bool:
    return MATTE_MODEL.exists()


class PersonMatte:
    _sess = None

    def __init__(self):
        if PersonMatte._sess is None:
            import onnxruntime as ort
            PersonMatte._sess = ort.InferenceSession(str(MATTE_MODEL), providers=["CPUExecutionProvider"])
        self.rec = None

    def reset(self) -> None:
        self.rec = None

    def __call__(self, f: np.ndarray) -> np.ndarray:
        """Khung BGR → mặt nạ người 0..1 (float32) cùng cỡ khung. Gọi liên tiếp theo thời gian; đổi cảnh → reset()."""
        H, W = f.shape[:2]
        k = MATTE_LONG / max(W, H)
        mw, mh = max(16, int(round(W * k / 4)) * 4), max(16, int(round(H * k / 4)) * 4)
        x = f if (mw, mh) == (W, H) else cv2.resize(f, (mw, mh), interpolation=cv2.INTER_AREA)
        x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        reps = 1
        if self.rec is None:   # khung đầu: chạy 3 lần cho trạng thái hồi quy ổn định
            self.rec, reps = [np.zeros((1, 1, 1, 1), np.float32)] * 4, 3
        for _ in range(reps):
            _, pha, *self.rec = self._sess.run(None, {"src": x, "r1i": self.rec[0], "r2i": self.rec[1], "r3i": self.rec[2],
                                                      "r4i": self.rec[3], "downsample_ratio": np.array([0.5], np.float32)})
        m = pha[0, 0]
        return m if (mw, mh) == (W, H) else cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)


def _cut_person(gf: np.ndarray, m: np.ndarray, x: int, y: int) -> tuple[np.ndarray, np.ndarray, float]:
    """Khoét chỗ người khỏi đồ hoạ: alpha × (1 − mặt nạ). Trả (khung mới, mặt nạ vùng đồ hoạ, tỉ lệ chữ bị che)."""
    h, w = gf.shape[:2]
    H, W = m.shape
    reg = np.zeros((h, w), np.float32)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 > x0 and y1 > y0:
        reg[y0 - y:y1 - y, x0 - x:x1 - x] = m[y0:y1, x0:x1]
    a = gf[:, :, 3].astype(np.float32)
    out = gf.copy()
    out[:, :, 3] = (a * (1 - reg) + 0.5).astype(np.uint8)
    return out, reg, float((a * reg).sum() / max(1.0, a.sum()))


def _text_alpha(a: dict, params: dict, MW: int, MH: int) -> tuple[dict, np.ndarray, float]:
    """Mở trang scene đúng tham số: qa (box, land…) + kênh alpha lúc chữ vừa vào đủ, thu về MW×MH (0..1)."""
    import io
    from PIL import Image
    from studio import motionlib
    spec = motionlib.spec_for(a, params=params)
    with motionlib.HtmlPage(a["dir"] / spec["entry"], spec["params"], spec["canvas"]) as pg:
        qa = pg.page.evaluate("() => (window.SCENE_MOTION || {}).qa || null") or {}
        D = float(pg.info.get("duration") or params.get("dur") or 1.2)
        tl = min(float(qa.get("full_at") or (float(qa.get("land") or 0.4) + 0.1)), D - 0.1)
        png = pg.frame(tl)
        qa["errors"] = pg.errors
    al = Image.open(io.BytesIO(png)).convert("RGBA").getchannel("A").resize((MW, MH), Image.BILINEAR)
    return qa, np.asarray(al, np.float32) / 255.0, tl


def _shift_occ(al: np.ndarray, m: np.ndarray, dy: int) -> float:
    """Tỉ lệ nét chữ (alpha) bị mặt nạ m che khi dời chữ dy điểm theo chiều dọc."""
    H = al.shape[0]
    if dy >= 0:
        a, mm = al[:H - dy], m[dy:]
    else:
        a, mm = al[-dy:], m[:H + dy]
    return float((a * mm).sum() / max(1e-6, al.sum()))


def _person_masks(job: Path, src: dict, sh: list[dict], ts: list[float], MW: int, MH: int) -> list[np.ndarray]:
    """Mặt nạ người (RVM, ảnh tĩnh MW×MH) ở các thời điểm; bỏ màn chữ; chỉ giữ mảng người đủ lớn (≥ 1,5% khung)."""
    ms = []
    for t in ts:
        shot = shot_at(sh, t)
        if shot["kind"] == "card":
            continue
        mt = PersonMatte()(still(job, src, shot, t, MW, MH))
        n_cc, lab, stats, _ = cv2.connectedComponentsWithStats((mt > 0.5).astype(np.uint8), connectivity=8)
        if n_cc > 1:   # bỏ nhiễu (trần nhà, đèn) làm đo sai đỉnh đầu
            keep = [i for i in range(1, n_cc) if stats[i, cv2.CC_STAT_AREA] >= 0.015 * MW * MH]
            mt = mt * np.isin(lab, keep).astype(np.float32)
        ms.append(mt)
    return ms


def _rects_mask(rects: list[dict], sx: float, sy: float, MW: int, MH: int, pad: int = 2) -> np.ndarray:
    k = np.zeros((MH, MW), np.float32)
    for r in rects or []:
        x0, y0 = int(r["x"] * sx) - pad, int(r["y"] * sy) - pad
        k[max(0, y0):max(0, y0 + int(r["h"] * sy) + 2 * pad), max(0, x0):max(0, x0 + int(r["w"] * sx) + 2 * pad)] = 1.0
    return k


def plan_behind(job: Path, e: dict, src: dict, sh: list[dict]) -> None:
    """Chữ sau người (Keyword Burst, Pinned Title…) — quyết định TRƯỚC khi render, trên ảnh tĩnh 540 ngang (preview và
    final ra cùng kết quả): mặt nạ người (RVM) ở nhiều lúc × NÉT CHỮ THẬT (chụp trang lúc đủ chữ) → thử dời dọc:
      · chưa ép y: chọn chỗ người che gần target_occlusion phần chữ ĐƯỢC khoét (tiêu đề / từ khoá) trong y_band;
      · phần KHÔNG khoét (qa.keep: nhãn con, dòng nhỏ · qa.dots: dấu nặng) không tính là bị che, và nhãn con không được
        nằm trên vùng đầu;
      · không chỗ nào hợp lệ (cận mặt, đầu sát mép trên, người xoay/sát máy) → chữ TRƯỚC người, dời né vùng đầu trong
        front_band; không có người → giữ chỗ.
    Family có auto_layout (tiêu đề ghim): chọn bố cục nhãn con theo vị trí người trước (giữa → sides, lệch → list phía
    trống). Ghi g['behind_plan']; sửa g['params'] (y, layout, side) khi tự đặt."""
    from studio import motionlib, scenes
    for g in e.get("graphics", []):
        mode = g.get("behind")
        if not mode and not g.get("layout_auto"):
            continue
        cfg = scenes.load(g["scene"]).get("behind", {}) if g.get("scene") else {}
        plan = g["behind_plan"] = {"mode": mode, "use": False}
        if not matte_ready():
            plan["reason"] = "chưa có mô hình tách người (assets/models/rvm_mobilenetv3_fp32.onnx) → chữ trước người"
            continue
        a = motionlib.get(g["id"])
        cw, ch = a["canvas"]
        MW = 540
        MH = int(round(MW * e["out"]["h"] / e["out"]["w"] / 2)) * 2
        sx, sy = MW / cw, MH / ch
        qa, al, tl = _text_alpha(a, g["params"], MW, MH)
        land = float(qa.get("land") or 0.4)
        # đo người nhiều lúc trong khi chữ đứng: từ khoá 3 lúc (vào đủ · giữa · sắp tan), tiêu đề ghim mỗi `every` giây
        every = cfg.get("every")
        s0 = min(g["t1"] - 0.05, g["t0"] + (land if every else tl))
        s1 = g["t1"] - 0.15
        n = 3 if not every else int(np.clip(round((s1 - s0) / float(every)) + 1, 3, 8))
        ts = sorted({round(float(x), 3) for x in np.linspace(s0, max(s0, s1), n)})
        ms = _person_masks(job, src, sh, ts, MW, MH)
        if not ms:
            plan["reason"] = "màn chữ / nền đen — không có người"
            continue
        m = np.max(ms, axis=0)   # hợp các lúc: dùng cho đỉnh đầu / vùng đầu (thận trọng)
        person = max(float((x > 0.5).mean()) for x in ms)
        plan["person"] = round(person, 3)
        if g.get("layout_auto"):   # bố cục nhãn con né người: đứng giữa → 2 bên đầu, lệch → cột phía trống
            col = m[int(0.12 * MH):int(0.45 * MH)].mean(axis=0)   # người chiếm bao nhiêu mỗi cột, ở tầm tiêu đề/nhãn
            if person < cfg.get("min_person", 0.03) or col.mean() < 0.03:
                lay, side = "list", "left"
            else:   # đo KHOẢNG TRỐNG thật 2 bên (cột nhãn con ~40% bề ngang mỗi bên), không theo tâm người
                cl, cr = float(col[:int(0.42 * MW)].mean()), float(col[int(0.58 * MW):].mean())
                plan["person_left"], plan["person_right"] = round(cl, 3), round(cr, 3)
                lay, side = ("sides", None) if max(cl, cr) < 0.2 else ("list", "left" if cl <= cr else "right")
            g["params"]["layout"] = lay
            if side:
                g["params"]["side"] = side
            plan["layout"] = lay + (f"/{side}" if side else "")
            qa, al, tl = _text_alpha(a, g["params"], MW, MH)
        if not mode:
            plan["reason"] = f"bố cục {plan.get('layout')} (behind=False → trước người)"
            continue
        if person < cfg.get("min_person", 0.03):
            plan["reason"] = f"không thấy người sau chữ (người {person:.0%} khung) → chữ trước người"
            continue
        box = qa.get("box")
        if not box or al.sum() < 1:
            plan["reason"] = "template không báo khung chữ (qa.box) → chữ trước người"
            continue
        keep = _rects_mask((qa.get("keep") or []) + (qa.get("dots") or []), sx, sy, MW, MH)
        items_m = _rects_mask(qa.get("items") or [], sx, sy, MW, MH, pad=0)
        al_c = al * (1 - keep)   # phần được phép nằm sau người (tiêu đề / từ khoá)
        if al_c.sum() < 1:
            plan["reason"] = "không có phần chữ được khoét → chữ trước người"
            continue
        cols = np.where(al_c.max(axis=0) > 0.1)[0]
        rows_t = np.where(al.max(axis=1) > 0.1)[0]
        hit = np.where((m[:, cols.min():cols.max() + 1] > 0.5).mean(axis=1) > 0.06)[0]
        head = int(hit[0]) if len(hit) else None
        plan["head_top"] = round(head / MH, 3) if head is not None else None
        hz = np.zeros_like(m)   # vùng đầu: đỉnh đầu → ~1,35 bề ngang đầu
        if head is not None:
            r = min(MH - 1, head + int(0.05 * MH))
            hh = int(np.clip(1.35 * float((m[r] > 0.5).sum()), 0.12 * MH, 0.35 * MH))
            hz[head:head + hh] = m[head:head + hh]
        cy0 = (box["y"] + box["h"] / 2) / ch                      # tâm chữ hiện tại (tỉ lệ khung) = tham số y của trang
        lo = int(cfg.get("top_limit", 0.10) * MH) - int(rows_t.min())   # dời lên tối đa: cả dòng nhỏ ≥ mép trên an toàn
        hi = int(0.76 * MH) - int(rows_t.max())                     # dời xuống tối đa: đáy ≤ 76% (vùng tên/mô tả TikTok)
        lo, hi = max(lo, int((0.14 - cy0) * MH)), min(hi, int((0.72 - cy0) * MH))   # trang kẹp y
        dys = list(range(lo, hi + 1, 4)) if not g.get("y_fixed") and hi >= lo else [0]
        if 0 not in dys and not g.get("y_fixed"):
            dys.append(0)
        band = cfg.get("y_band", [0.14, 0.42])   # chữ SAU người chỉ ở tầm đầu như mẫu (15–35% H), không sau ngực
        fband = cfg.get("front_band", [0.14, 0.72])
        per = {dy: [_shift_occ(al_c, x, dy) for x in ms] for dy in dys}
        occs = {dy: float(np.mean(v)) for dy, v in per.items()}     # che trung bình các lúc
        peak = {dy: max(v) for dy, v in per.items()}                # lúc che nhiều nhất
        ih = {dy: (_shift_occ(items_m, hz, dy) if items_m.any() else 0.0) for dy in dys}   # nhãn con đè vùng đầu
        tgt, lim = cfg.get("target_occlusion", 0.22), cfg.get("max_occlusion", 0.35)
        lim_pk = cfg.get("max_occlusion_peak", 0.5)
        dz = [(int(d["x"] * sx), int(d["y"] * sy), max(1, int(d["w"] * sx)), max(1, int(d["h"] * sy)))
              for d in qa.get("dots") or []]

        def dot_occ(x: np.ndarray, d: int) -> float:
            v = [float(x[max(0, y0 + d):max(0, y0 + d + h), x0:x0 + w].mean()) for x0, y0, w, h in dz
                 if 0 <= y0 + d < MH]
            return max(v) if v else 0.0
        ok = [dy for dy in dys if 0.06 <= occs[dy] <= lim and peak[dy] <= lim_pk and ih[dy] <= 0.08
              and band[0] <= cy0 + dy / MH <= band[1]]
        if g.get("y_fixed"):
            dy = 0
            use = mode is True or occs[0] <= lim
        elif ok:
            # trong ±6% quanh mức che đích → chọn chỗ gần vị trí theme nhất; không có thì chỗ che gần đích nhất
            dy = min(ok, key=lambda d: (max(0.0, abs(occs[d] - tgt) - 0.06), abs(d)))
            use = True
        elif mode is True:
            dy, use = min(dys, key=lambda d: (abs(occs[d] - tgt), abs(d))), True
        else:
            dy, use = None, False
        if not use:   # chữ trước người: né VÙNG ĐẦU, ưu tiên chỗ gần vị trí theme, trong front_band
            inband = [d for d in dys if band[0] <= cy0 + d / MH <= band[1]] or dys
            vua = [d for d in inband if 0.06 <= occs[d] <= lim]      # độ cao người che vừa phải
            yen = [d for d in vua if peak[d] <= lim_pk]               # … và lúc nào cũng không che quá
            if all(occs[d] < 0.06 for d in inband):
                reason = "người không chạm chữ ở tầm đầu"
            elif not vua:
                reason = f"người che > {lim:.0%} nét chữ ở mọi độ cao tầm đầu (cận mặt / đầu sát mép trên)"
            elif not yen:
                reason = f"người cử động / sát máy: có lúc che > {lim_pk:.0%} nét chữ"
            else:
                reason = "nhãn con sẽ đè lên đầu ở mọi độ cao hợp lệ"
            dy = 0
            if head is not None and not g.get("y_fixed"):
                fd = [d for d in dys if fband[0] <= cy0 + d / MH <= fband[1]] or [0]
                h0 = _shift_occ(al, hz, 0)
                hzo = {d: _shift_occ(al, hz, d) for d in fd}
                if h0 > 0.02:
                    best = min(hzo.values())
                    dy = min((d for d in fd if hzo[d] <= best + 0.01), key=abs)
                    reason += f" → chữ TRƯỚC người, dời né đầu (che đầu {h0:.0%} → {hzo[dy]:.0%})"
                    plan["head_overlap"] = round(hzo[dy], 3)
                else:
                    reason += " → chữ TRƯỚC người (không đè đầu)"
            else:
                reason += " → chữ TRƯỚC người" + (" — y ép tay, soát ảnh qa" if g.get("y_fixed") else "")
            plan["reason"] = reason + (f" · bố cục {plan['layout']}" if plan.get("layout") else "")
            if dy:
                g["params"]["y"] = plan["y"] = round(cy0 + dy / MH, 3)
            plan["occlusion_est"] = round(occs.get(dy, 0.0), 3)
            continue
        if dy and not g.get("y_fixed"):
            g["params"]["y"] = plan["y"] = round(cy0 + dy / MH, 3)
        plan["occlusion_est"] = round(occs[dy], 3)
        plan["occlusion_peak_est"] = round(peak[dy], 3)
        if dz:
            plan["dot_hidden_est"] = round(max(dot_occ(x, dy) for x in ms), 3)   # build giữ dấu nổi, không khoét
        plan["use"] = True
        plan["reason"] = (f"chữ SAU người, người che ~{occs[dy]:.0%} phần chữ khoét được"
                          + (f", tự đặt y={plan['y']}" if plan.get("y") is not None else (", y ép tay" if g.get("y_fixed") else ""))
                          + (f" (> {lim:.0%} nhưng ép behind=True)" if occs[dy] > lim else "")
                          + (f" · bố cục {plan['layout']}" if plan.get("layout") else ""))


def _out_still(job: Path, e: dict, src: dict, sh: list[dict], t: float, W: int, H: int) -> np.ndarray:
    """Khung RA tại giây t đúng như bản dựng (đặt khung/zoom theo cảnh + chỉnh màu), chưa có chữ/đồ hoạ."""
    f = still(job, src, shot_at(sh, t), t, W, H)
    if e.get("grade", "cinematic"):
        f = _grade(W, H, e.get("grade", "cinematic"))(f)
    return f


def frame_grid(job_id: str, ts: list[float]) -> list[Path]:
    """`vs.py edit frame`: ảnh khung RA ở các giây + lưới toạ độ 0,1 (x ngang, y dọc theo tỉ lệ khung) → chọn x, y cho
    Scene chỉ vào chi tiết (C09 Detail Spotlight) / ép y chữ. Lưu jobs/<id>/frames/out_<giây>.jpg."""
    job = project.job_path(job_id)
    e = json.loads((job / "edit.json").read_text(encoding="utf-8"))
    src = project.load_sources(job)
    focus_faces(job, e, src)
    sh, _ = shots(e, src)
    W, H = e["out"]["w"], e["out"]["h"]
    out_dir = job / "frames"
    out_dir.mkdir(exist_ok=True)
    paths = []
    for t in ts:
        f = _out_still(job, e, src, sh, t, W, H).copy()
        ov = f.copy()
        for k in range(1, 10):
            x, y = int(W * k / 10), int(H * k / 10)
            cv2.line(ov, (x, 0), (x, H), (255, 255, 255), 2)
            cv2.line(ov, (0, y), (W, y), (255, 255, 255), 2)
        f = cv2.addWeighted(ov, 0.45, f, 0.55, 0)
        for k in range(1, 10):
            x, y = int(W * k / 10), int(H * k / 10)
            for (px, py, txt) in ((x + 6, 40, f"x{k / 10:.1f}"), (8, y - 8, f"y{k / 10:.1f}")):
                cv2.putText(f, txt, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 6, cv2.LINE_AA)
                cv2.putText(f, txt, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(f, f"{t:.2f}s", (W - 230, H - 40), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 4, cv2.LINE_AA)
        p = out_dir / f"out_{t:06.2f}.jpg"
        cv2.imwrite(str(p), cv2.resize(f, (W // 2, H // 2)), [cv2.IMWRITE_JPEG_QUALITY, 88])
        paths.append(p)
    return paths


def plan_loupe(job: Path, e: dict, src: dict, sh: list[dict]) -> None:
    """Kính lúp (C09 Detail Spotlight bản full): cắt khung RA đúng giữa đoạn chỉ (cỡ 1080 — chữ, chi tiết nét) →
    params['loupe'] = file:/// + 'loupe_v' = hash ảnh. Ảnh trong kính là khung tĩnh lúc đó (cảnh đứng yên là khớp)."""
    import hashlib
    from studio import scenes
    work = job / "render"
    work.mkdir(exist_ok=True)
    for gi, g in enumerate(e.get("graphics", [])):
        if not g.get("scene"):
            continue
        prof = scenes.load(g["scene"])
        p = g["params"]
        if not prof.get("loupe") or (p.get("zoom") is not None and float(p["zoom"]) <= 0):   # zoom=0 = tắt kính lúp
            continue
        if p.get("preset") not in prof["loupe"].get("presets", ["full"]):
            continue
        W, H = e["out"]["w"], e["out"]["h"]
        t = (g["t0"] + g["t1"]) / 2
        f = _out_still(job, e, src, sh, t, W, H)
        out = work / f"loupe_g{gi + 1:02d}.jpg"
        cv2.imwrite(str(out), f, [cv2.IMWRITE_JPEG_QUALITY, 92])
        p["loupe"] = out.resolve().as_uri()
        p["loupe_v"] = hashlib.sha1(out.read_bytes()).hexdigest()[:10]


def _prog(t: float, a: float, b: float) -> float:
    return (1.0 if t >= b else 0.0) if b <= a else min(1.0, max(0.0, (t - a) / (b - a)))


def _inout(x: float) -> float:
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


class ProofPainter:
    """C08 Evidence Frame chế độ CLIP: phát clip bằng chứng THẬT vào đúng ô cửa sổ trang scene chừa ra (qa.window) từ lúc
    khung đứng yên (qa.live_t), phóng dần tới điểm (qa.zoom — khớp transform-origin/scale của trang), mờ theo lúc ra
    (qa.exit). Vẽ vào khung TRƯỚC khi đè đồ hoạ (đồ hoạ thủng đúng ô → clip lộ ra, băng keo/tem vẫn nằm trên)."""

    def __init__(self, job: Path, src: dict, g: dict, W: int, H: int):
        qa = g.get("text_qa") or {}
        pc = g.get("proof_clip")
        self.ok = bool(qa.get("live") and qa.get("window") and pc and pc.get("src") in src)
        self.reader = None
        if not self.ok:
            return
        cw, ch = (g.get("info") or g)["canvas"]
        w, kx, ky = qa["window"], W / cw, H / ch
        self.x, self.y = round(w["x"] * kx), round(w["y"] * ky)
        self.w, self.h = max(2, round(w["w"] * kx)), max(2, round(w["h"] * ky))
        self.g0, self.t_live = g["t0"], g["t0"] + float(qa["live_t"])
        self.e0, self.e1 = g["t0"] + float(qa["exit"][0]), g["t0"] + float(qa["exit"][1])
        self.zoom = qa.get("zoom")
        s = src[pc["src"]]
        self.path, self.sw, self.sh, self.s0 = job / s["file"], s["width"], s["height"], float(pc["s0"])

    def active(self, t: float) -> bool:
        return self.ok and self.t_live - 1e-6 <= t < self.e1

    def paint(self, f: np.ndarray, t: float, fps: float) -> np.ndarray:
        """f: khung BGR (H×W) hoặc BGRA (lớp trong suốt — alpha = độ đục clip). Trả khung đã vẽ (bản sao)."""
        if not self.active(t):
            return f
        if self.reader is None:
            self.reader = Reader(self.path, self.s0 + max(0.0, t - self.t_live), self.e1 - t + 0.3, fps, self.sw, self.sh)
        img = self.reader.read()
        sh_, sw_ = img.shape[:2]
        a = self.w / self.h
        if sw_ / sh_ > a:   # cắt cho kín ô (như object-fit: cover)
            cw_, ch_ = sh_ * a, float(sh_)
        else:
            cw_, ch_ = float(sw_), sw_ / a
        x0, y0 = (sw_ - cw_) / 2, (sh_ - ch_) / 2
        if self.zoom:   # phóng quanh điểm (zx, zy) của ô — y như scale + transform-origin của trang
            z = 1 + (float(self.zoom["k"]) - 1) * _inout(_prog(t, self.g0 + self.zoom["t0"], self.g0 + self.zoom["t1"]))
            zx, zy = float(self.zoom["zx"]), float(self.zoom["zy"])
            x0, y0, cw_, ch_ = x0 + zx * cw_ * (1 - 1 / z), y0 + zy * ch_ * (1 - 1 / z), cw_ / z, ch_ / z
        sc = self.w / cw_
        M = np.float32([[sc, 0, -x0 * sc], [0, sc, -y0 * sc]])
        win = cv2.warpAffine(img, M, (self.w, self.h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        k = 1 - _prog(t, self.e0, self.e1) ** 3
        out = f.copy()
        Hh, Ww = out.shape[:2]
        X0, Y0, X1, Y1 = max(0, self.x), max(0, self.y), min(Ww, self.x + self.w), min(Hh, self.y + self.h)
        if X1 <= X0 or Y1 <= Y0:
            return out
        part = win[Y0 - self.y:Y1 - self.y, X0 - self.x:X1 - self.x].astype(np.float32)
        if out.shape[2] == 4:   # lớp trong suốt (CapCut micro): rgb = clip, alpha = độ đục
            out[Y0:Y1, X0:X1, :3] = part.astype(np.uint8)
            out[Y0:Y1, X0:X1, 3] = np.uint8(round(255 * k))
        else:
            roi = out[Y0:Y1, X0:X1].astype(np.float32)
            out[Y0:Y1, X0:X1] = (roi * (1 - k) + part * k).astype(np.uint8)
        return out

    def close(self) -> None:
        if self.reader:
            self.reader.close()
            self.reader = None


def render_graphics(e: dict) -> list[dict]:
    """Render (cache) từng đồ hoạ của edit.json bằng Motion Engine. Tham số chữ đổi → render mới (~2 phút / thẻ)."""
    from studio import motionlib
    out = []
    for g in e.get("graphics", []):
        a = motionlib.get(g["id"])
        t = time.time()
        info = motionlib.render(a, params=g["params"])
        qa = None
        if g.get("scene"):   # template Scene Library tự báo chữ tràn / cỡ chữ
            from studio import scenes
            qa = scenes.text_qa(a, g["params"])
        out.append({**g, "info": info, "seconds": round(time.time() - t, 1), "text_qa": qa})
    return out


def run(job_id: str, final: bool = False) -> dict:
    job = project.job_path(job_id)
    e = json.loads((job / "edit.json").read_text(encoding="utf-8"))
    src = project.load_sources(job)
    out_cfg = e["out"]
    scale = 1.0 if final else 0.5
    W, H, fps = int(out_cfg["w"] * scale) // 2 * 2, int(out_cfg["h"] * scale) // 2 * 2, out_cfg["fps"]
    work = job / "render"
    work.mkdir(exist_ok=True)
    t_start = time.time()
    focus_faces(job, e, src)
    sh, trans = shots(e, src)
    T = e["duration"]
    N = int(round(T * fps))

    plan_behind(job, e, src, sh)   # chữ sau người / bố cục: quyết định + tự đặt y TRƯỚC khi render đồ hoạ
    plan_loupe(job, e, src, sh)    # kính lúp C09: khung RA đúng lúc chỉ
    graphics = render_graphics(e)
    proofs = {gi: pp for gi, g in enumerate(graphics) if (pp := ProofPainter(job, src, g, W, H)).ok}   # C08 clip thật
    avoid = []   # đồ hoạ giữ chữ động (tiêu đề ghim) → chữ động né vùng của nó
    for g in graphics:
        ar = (g.get("text_qa") or {}).get("area")
        if g.get("captions_keep") and ar:
            cw, ch = g["info"]["canvas"]
            avoid.append((g["t0"], g["t1"], (ar["x"] * W / cw, ar["y"] * H / ch, ar["w"] * W / cw, ar["h"] * H / ch)))
    with Kinetic(e.get("style", "cinematic"), W, H, (e.get("style_cfg") or {}).get("skin")) as kin:
        placements = plan_captions(job, e, src, sh, kin, W, H, avoid)
        t_cap = time.time()
        cap_idx = kin.frames(T, fps, work / "captions")
        captured = kin.captured
    t_cap = time.time() - t_cap
    for g in graphics:   # vào đồ hoạ bằng chuyển cảnh (mẫu: 1 khung loé trắng-đen); ra = animation tự nhoè về trong suốt
        if g["trans"] != "cut":
            trans = sorted(set(trans) | {(round(g["t0"], 4), g["trans"])})
    from studio import scenes
    sfx = [ev for g in graphics if (prof := scenes.for_motion(g["id"])) for ev in scenes.sfx_events(prof, g)]
    audio = build_audio(job, e, src, work, sfx)

    name = "final" if final else "preview"
    out = job / f"{name}.mp4"
    tmp = job / f"{name}.tmp.mp4"
    interp = cv2.INTER_CUBIC if final else cv2.INTER_LINEAR
    enc = ["-preset", "medium", "-crf", "18"] if final else ["-preset", "veryfast", "-crf", "23"]
    writer = subprocess.Popen([config.FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                               "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                               "-c:v", "libx264", *enc, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                               "-ar", str(SR), "-movflags", "+faststart", "-shortest", str(tmp)], stdin=subprocess.PIPE)
    logo = _logo(e, W, H)
    grade = _grade(W, H, e.get("grade", "cinematic")) if e.get("grade", "cinematic") else None
    card_ranges = [(c["t0"], c["t1"]) for c in e["cards"]]
    # logo ẩn trong lúc đồ hoạ phủ kín (trừ đoạn nhoè cuối 0,3s)
    card_ranges += [(g["t0"], g["t1"] - 0.12) for g in graphics if g.get("covers", True)]   # micro (không phủ) giữ logo
    card_ranges += [(g["t0"], g["t1"]) for g in graphics if g.get("hide_logo")]   # tiêu đề ghim chiếm góc trên → ẩn logo
    greaders: dict[int, GraphicReader] = {}
    behind = {gi for gi, g in enumerate(graphics) if (g.get("behind_plan") or {}).get("use")}
    matte = PersonMatte() if behind else None
    keep_dots = {}   # vùng KHÔNG khoét của đồ hoạ sau người: dấu nặng (đầu che = sai chữ) + nhãn con / dòng nhỏ
    for gi in behind:
        k = np.zeros((H, W), np.float32)
        cw, ch = graphics[gi]["info"]["canvas"]
        tq = graphics[gi].get("text_qa") or {}
        for d in (tq.get("dots") or []) + (tq.get("keep") or []):
            x0, y0 = int(d["x"] * W / cw) - 2, int(d["y"] * H / ch) - 2
            k[max(0, y0):max(0, y0 + int(d["h"] * H / ch) + 4), max(0, x0):max(0, x0 + int(d["w"] * W / cw) + 4)] = 1.0
        keep_dots[gi] = k if k.any() else None
    matte_key = None
    masks = {gi: {} for gi in behind}   # mặt nạ vùng đồ hoạ theo số khung clip → xuất CapCut dùng lại
    occl = {gi: [] for gi in behind}
    cap_cache = {}
    prev_frame, last_of_prev = None, None
    black = np.zeros((H, W, 3), np.uint8)
    try:
        for s in sh:
            i0, i1 = int(np.ceil(s["t0"] * fps - 1e-6)), min(N, int(np.ceil(s["t1"] * fps - 1e-6)))
            if i1 <= i0:
                continue
            reader = None
            if s["kind"] != "card":
                ss = src[s["src"]]
                reader = Reader(job / ss["file"], s["s0"] + (i0 / fps - s["t0"]) * s["speed"],
                                (i1 - i0) / fps * s["speed"], fps / s["speed"], ss["width"], ss["height"])
            last_of_prev = prev_frame
            for i in range(i0, i1):
                t = i / fps
                if reader is None:
                    f = black.copy()
                else:
                    f = place(reader.read(), W, H, zoom_at(s, t), s["focus"], s["fit"], interp)
                    if grade:
                        f = grade(f)
                    if s.get("glass"):   # màn chữ kính mờ (phong cách): hình vẫn chạy, nhoè + tối, vào/ra 0,2s
                        f = _glass(f, min(1.0, (t - s["t0"]) / 0.2, (s["t1"] - t) / 0.2))
                m_full = None
                act = [gi for gi in behind if graphics[gi]["t0"] <= t < graphics[gi]["t1"]]
                if act:   # mặt nạ người trên khung CHƯA đè đồ hoạ; đổi cảnh / đổi đồ hoạ → trạng thái mô hình làm lại
                    if matte_key != (s["t0"], act[0]):
                        matte.reset()
                        matte_key = (s["t0"], act[0])
                    m_full = matte(f)
                for pp in proofs.values():   # clip bằng chứng phát vào ô cửa sổ (đồ hoạ thủng đúng ô, đè lên sau)
                    if pp.active(t):
                        f = pp.paint(f, t, fps)
                for gi, g in enumerate(graphics):   # đồ hoạ phủ khung: trên hình, dưới chuyển cảnh/logo/chữ
                    if g["t0"] <= t < g["t1"]:
                        if gi not in greaders:
                            greaders[gi] = GraphicReader(g["info"], g["t0"], W, H)
                        gf = greaders[gi].at(t)
                        if gf is not None:
                            f = f.copy()
                            gr = greaders[gi]
                            if m_full is not None and gi in behind:   # chữ nằm sau người
                                mk = m_full if keep_dots[gi] is None else m_full * (1 - keep_dots[gi])
                                gf, reg, oc = _cut_person(gf, mk, gr.x, gr.y)
                                masks[gi][gr.i] = (reg * 255 + 0.5).astype(np.uint8)
                                if t >= g["t0"] + float((g.get("text_qa") or {}).get("land") or 0.3):
                                    occl[gi].append(oc)
                            _blend(f, gf, gr.x, gr.y)
                    elif gi in greaders and t >= g["t1"]:
                        greaders.pop(gi).close()
                base = f
                for T0, kind in trans:
                    if kind == "flash" and abs(t - T0) <= FLASH / fps:
                        f = _bleach(f, 1 - abs(t - T0) * fps / (FLASH + 0.5))
                    elif kind == "dip":
                        if T0 - DIP_OUT <= t < T0:
                            q = (T0 - t) / DIP_OUT
                            f = (_bleach(f, (1 - q) * 0.6).astype(np.float32) * q).astype(np.uint8)
                        elif T0 <= t < T0 + DIP_IN:
                            f = (f.astype(np.float32) * ((t - T0) / DIP_IN)).astype(np.uint8)
                    elif kind == "wipe" and T0 <= t < T0 + WIPE and last_of_prev is not None:
                        q = 1 - (1 - (t - T0) / WIPE) ** 3
                        bx = int(W * q)
                        f = f.copy()
                        f[:, bx:] = last_of_prev[:, bx:]
                        bw = max(2, W // 80)
                        f[:, max(0, bx - bw):min(W, bx + bw)] = 0
                prev_frame = base
                in_card = any(a <= t < b for a, b in card_ranges)
                if logo is not None and not in_card:
                    f = f.copy() if f is base else f
                    _blend(f, *logo)
                ent = cap_idx[i] if i < len(cap_idx) else None
                if ent and any(g["t0"] - 1e-6 <= t < g["t1"] - 0.3 for g in graphics if not g.get("captions_keep")):
                    ent = None   # đồ hoạ phủ khung: tiêu đề đồ hoạ thay chữ (chữ câu trước đang rút cũng tắt)
                if ent:
                    if ent[0] not in cap_cache:
                        cap_cache.clear()
                        cap_cache[ent[0]] = cv2.imread(str(work / "captions" / ent[0]), cv2.IMREAD_UNCHANGED)
                    f = f.copy() if f is base else f
                    _blend(f, cap_cache[ent[0]], ent[1], ent[2])
                writer.stdin.write(np.ascontiguousarray(f).tobytes())
            if reader:
                reader.close()
    finally:
        for gr in greaders.values():
            gr.close()
        for pp in proofs.values():
            pp.close()
        writer.stdin.close()
        writer.wait()
    lufs = _normalize_loudness(tmp, float(e["audio"].get("voice_lufs", -14.0)))
    tmp.replace(out)
    name_b = {}
    for gi in behind:   # mặt nạ người theo khung → `vs.py edit capcut` khoét lại chữ ở cỡ 1080 (chữ nét, không phóng)
        g, gr_box = graphics[gi], graphic_box(graphics[gi]["info"], W, H)
        mf = work / f"behind_{name}_g{gi + 1:02d}.npz"
        idx = sorted(masks[gi])
        if idx:
            np.savez_compressed(mf, idx=np.array(idx), m=np.stack([masks[gi][k] for k in idx]), box=np.array([*gr_box, W, H]))
        oc = occl[gi]
        name_b[gi] = {"use": True, "reason": g["behind_plan"]["reason"], "masks": mf.name if idx else None,
                      "occlusion_mean": round(float(np.mean(oc)), 3) if oc else None,
                      "occlusion_max": round(float(np.max(oc)), 3) if oc else None,
                      **{k: g["behind_plan"][k] for k in ("person", "head_top", "y", "occlusion_est") if k in g["behind_plan"]}}
    poster = job / f"{name}.jpg"
    key_blocks = [b for b in e["captions"] if any(ln["role"] == "key" for ln in b["lines"])] or e["captions"]
    if key_blocks:
        b = key_blocks[0]
        media.extract_frame(out, (b["last_end"] + b["end"]) / 2, poster)
    rep = {"output": out.name, "final": final, "size": [W, H], "fps": fps, "duration": T, "frames": N,
           "seconds": round(time.time() - t_start, 1), "caption_seconds": round(t_cap, 1),
           "caption_frames_captured": captured, "lufs": lufs, "face_check": face_ready(), "shots": sh, "transitions": trans,
           "placements": placements, "poster": poster.name,
           "sfx": [{"file": Path(f).name, "gain_db": gd, "at": at} for f, gd, at in sfx],
           "graphics": [{"id": g["id"], "t0": g["t0"], "t1": g["t1"], "mov": g["info"]["mov"], "covers": g.get("covers", True), "text_qa": g.get("text_qa"),
                         "bbox": g["info"]["bbox"], "canvas": g["info"]["canvas"], "fps": g["info"]["fps"],
                         "frames": g["info"]["frames"], "scene": g.get("scene"),
                         "proof_clip": g.get("proof_clip"),
                         "behind": name_b.get(gi) or ({**g["behind_plan"], "use": False} if g.get("behind_plan") else None),
                         "render_seconds": g["seconds"], "params": g["params"]} for gi, g in enumerate(graphics)]}
    (job / f"render_{name}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return rep
