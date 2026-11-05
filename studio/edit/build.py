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
        if cards:
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
def _js_blocks(e: dict) -> list[dict]:
    out = []
    for b in e["captions"]:
        lines = [{"role": ln["role"], "italic": ln.get("italic", False), "accent": ln.get("accent", False),
                  **({"morph_at": ln["morph_at"]} if ln.get("morph_at") is not None else {}),
                  "words": [{"text": w["text"], "t": w["t"]} for w in ln["words"]]} for ln in b["lines"]]
        out.append({"id": b["id"], "end": b["end"], "exit": b["exit"], "card": b["card"], "lines": lines,
                    **({"stagger": b["stagger"]} if b.get("stagger") else {}),
                    "align": "center", "x": 0.46, "y": b.get("y") or 0.47})
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


def plan_captions(job: Path, e: dict, src: dict, sh: list[dict], kin: Kinetic, W: int, H: int) -> list[dict]:
    """Chọn chỗ đặt từng khối: né mặt (OpenCV) + nằm trong vùng an toàn TikTok; màn chữ luôn ở giữa."""
    js = _js_blocks(e)
    boxes = kin.load(js)
    report = []
    for b, jb, bx in zip(e["captions"], js, boxes):
        times = [b["first"] + 0.05, (b["first"] + b["end"]) / 2, max(b["first"] + 0.05, b["end"] - 0.05)]
        fb = []
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
            cands = [(b["pos"], x, b.get("y") or yy) for yy in ([b["y"]] if b.get("y") else Y_OPTS)]
        else:
            cands = [(m, x, b.get("y") or yy) for m, x in PLACES for yy in ([b["y"]] if b.get("y") else Y_OPTS)]

        def score(c):
            r = _rect(c[0], c[1], c[2], w, h, W, H)
            return (10 * _overlap(r, fb) + 10 * _outside(r, W, H) + (0.15 if c[0] != "center" else 0)
                    + abs(c[2] - 0.47) * 1.0)
        m, x, y = min(cands, key=score)
        jb.update(align=m, x=x, y=y)
        r = _rect(m, x, y, w, h, W, H)
        report.append({"id": b["id"], "pos": m, "x": x, "y": y, "faces": fb, "face_overlap": round(_overlap(r, fb), 3),
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


def build_audio(job: Path, e: dict, src: dict, work: Path) -> Path:
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


def _grade(W: int, H: int):
    """Chỉnh màu "cinematic" như mẫu: tối viền (góc ×0,72) + nén vùng sáng (đường cong mềm, trắng tối đa ~94%).
    Áp cho người nói + cảnh minh hoạ, không áp màn chữ. Trả hàm f(frame) → frame."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    vig = (1 - 0.28 * np.clip((r - 0.35) / 0.65, 0, 1) ** 1.6)[..., None].astype(np.float32)
    x = np.arange(256, dtype=np.float32) / 255
    lut = np.clip(255 * (0.94 * x ** 1.06 + 0.02 * np.sin(np.pi * x)), 0, 255).astype(np.uint8)

    def apply(f: np.ndarray) -> np.ndarray:
        return (cv2.LUT(f, lut).astype(np.float32) * vig).astype(np.uint8)
    return apply


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

    with Kinetic(e.get("style", "cinematic"), W, H) as kin:
        placements = plan_captions(job, e, src, sh, kin, W, H)
        t_cap = time.time()
        cap_idx = kin.frames(T, fps, work / "captions")
        captured = kin.captured
    t_cap = time.time() - t_cap
    audio = build_audio(job, e, src, work)

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
    grade = _grade(W, H) if e.get("grade", "cinematic") == "cinematic" else None
    card_ranges = [(c["t0"], c["t1"]) for c in e["cards"]]
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
        writer.stdin.close()
        writer.wait()
    lufs = _normalize_loudness(tmp, float(e["audio"].get("voice_lufs", -14.0)))
    tmp.replace(out)
    poster = job / f"{name}.jpg"
    key_blocks = [b for b in e["captions"] if any(ln["role"] == "key" for ln in b["lines"])] or e["captions"]
    if key_blocks:
        b = key_blocks[0]
        media.extract_frame(out, (b["last_end"] + b["end"]) / 2, poster)
    rep = {"output": out.name, "final": final, "size": [W, H], "fps": fps, "duration": T, "frames": N,
           "seconds": round(time.time() - t_start, 1), "caption_seconds": round(t_cap, 1),
           "caption_frames_captured": captured, "lufs": lufs, "face_check": face_ready(), "shots": sh, "transitions": trans,
           "placements": placements, "poster": poster.name}
    (job / f"render_{name}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return rep
