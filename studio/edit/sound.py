"""Phân tích TIẾNG ĐỘNG cho video KHÔNG LỜI (POV / ASMR: rót nước, đá chạm ly, mở nắp) — numpy thuần.

Video có lời cắt theo mốc từng từ (asr.py); clip không lời thì không có từ để bám → bám vào tiếng động:
  • đường bao RMS bước 10ms (dB), lọc bỏ ù dưới 80Hz;
  • MỐC BẬT (onset): hiệu bậc nhất nửa sóng dương của log-RMS, lấy đỉnh cục bộ vượt (trung vị + k·MAD) trong cửa sổ ±1s,
    khoảng trơ 60ms (học thuật toán beat grid của ffmpeg-skill, 10/11) — rồi chỉnh mốc tới 1ms theo đường bao 1ms;
  • CỤM tiếng động (đoạn liên tục có tiếng) + ĐIỂM LẶNG (chỗ yên nhất giữa 2 cụm — chỗ đặt mép cắt an toàn).
Ngưỡng luôn TƯƠNG ĐỐI so với nền của chính clip (không dùng −35dB tuyệt đối kiểu silencedetect: tiếng rót khẽ trong
phòng yên ~−45dB sẽ bị coi là im lặng). Kết quả cache trong jobs/<id>/sound/<key>.json (theo hash file + VERSION).
"""

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from studio import config, media

VERSION = 1
SR = 16000
STEP = 0.01                # đường bao 10ms
ONSET_K = 1.5              # đỉnh lực bật phải vượt trung vị + k·MAD trong cửa sổ cục bộ
ONSET_WINDOW = 1.0         # ±1s
ONSET_REFRACTORY = 0.06    # 2 mốc bật gần hơn 60ms = 1 mốc
ONSET_MIN_RISE = 6.0       # dB: mức sau mốc phải cao hơn mức trước mốc ít nhất 6dB (lọc dao động nhỏ của nền)
ONSET_ABOVE = 9.0          # dB: tiếng sau mốc phải cao hơn nền ≥ 9dB
GAP_MERGE = 0.12           # 2 cụm cách nhau < 120ms = 1 cụm
MIN_CLUSTER = 0.03         # cụm ngắn hơn 30ms (và không có mốc bật) = nhiễu, bỏ
SHORT = 0.4                # cụm ≤ 0,4s = "bật gọn" (đá rơi, nắp bật); dài hơn = "kéo dài" (rót, xay, sủi)
PRE_GUARD = 0.04           # mép cắt phải trước tiếng ≥ 40ms (vuốt 30ms không ăn vào tiếng bật)
POST_GUARD = 0.05          # và sau đuôi tiếng ≥ 50ms


# ───────────────────────── đọc tiếng & đường bao ─────────────────────────
def load(path: Path, sr: int = SR) -> np.ndarray:
    """Tiếng mono float32 (đã lọc ù < 80Hz: tiếng tay cầm máy / điều hoà không lấn tiếng động nhỏ)."""
    out = subprocess.run([config.FFMPEG, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-af", "highpass=f=80", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(out, np.float32).copy()


def envelope(audio: np.ndarray, sr: int = SR, step: float = STEP) -> np.ndarray:
    """RMS từng khung `step` giây → dB (sàn −120)."""
    hop = max(1, int(round(sr * step)))
    n = len(audio) // hop
    if n == 0:
        return np.zeros(0, np.float32)
    rms = np.sqrt((audio[: n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1))
    return (20 * np.log10(rms + 1e-6)).astype(np.float32)


def onset_strength(db: np.ndarray) -> np.ndarray:
    """Hiệu bậc nhất NỬA SÓNG DƯƠNG của log-RMS (dB đã là log). Miền log quan trọng: tiếng khẽ bật lên cũng ra lực
    bật như tiếng to — đo trên biên độ thì đoạn to lấn hết, tiếng rót khẽ không có mốc nào."""
    if len(db) < 2:
        return np.zeros(len(db), np.float32)
    return np.concatenate([[0.0], np.maximum(0.0, np.diff(db))]).astype(np.float32)


def pick_onsets(strength: np.ndarray, step: float = STEP) -> list[int]:
    """Chỉ số các đỉnh cục bộ vượt trung vị + k·MAD trong ±ONSET_WINDOW, có khoảng trơ (giữ đỉnh mạnh hơn).
    Trung vị/MAD thay vì trung bình/độ lệch: vài tiếng rất mạnh không kéo ngưỡng lên trên mọi tiếng khác."""
    n = len(strength)
    if n < 3:
        return []
    half = max(1, int(round(ONSET_WINDOW / step)))
    refr = max(1, int(round(ONSET_REFRACTORY / step)))
    picked: list[int] = []
    for i in range(1, n - 1):
        s = strength[i]
        if s <= 0 or s < strength[i - 1] or s < strength[i + 1]:
            continue
        win = strength[max(0, i - half):min(n, i + half + 1)]
        med = float(np.median(win))
        mad = float(np.median(np.abs(win - med)))
        if s <= med or s < med + ONSET_K * mad:
            continue
        if picked and i - picked[-1] < refr:
            if s > strength[picked[-1]]:
                picked[-1] = i
            continue
        picked.append(i)
    return picked


def _refine(audio: np.ndarray, sr: int, db: np.ndarray, i: int) -> float:
    """Mốc bật chính xác tới 1ms: từ 30ms trước khung bật, ms đầu tiên mà mức 1ms vượt mức ĐỈNH của nền ngay trước
    (p90 các ms trong 50ms trước đó) +3dB, liền 2ms. Lấy p90 chứ không lấy trung vị: nền là tiếng rót (ồn dao động
    ±vài dB từng ms) thì trung vị làm mốc đá rơi giữa lúc rót bị sớm ~20ms (đo 10/11 trên tiếng tổng hợp)."""
    ms = sr // 1000
    hop = int(sr * STEP)
    p0, a0 = max(0, (i - 8) * hop), max(0, (i - 3) * hop)
    a1 = min(len(audio), (i + 2) * hop)

    def lv(x: np.ndarray) -> np.ndarray:
        k = len(x) // ms
        return 20 * np.log10(np.sqrt((x[: k * ms].reshape(k, ms).astype(np.float64) ** 2).mean(1)) + 1e-6) if k else np.zeros(0)
    pre, cur = lv(audio[p0:a0]), lv(audio[a0:a1])
    if len(cur) < 2:
        return round(i * STEP, 3)
    pre_db = float(np.percentile(pre, 90)) if len(pre) >= 5 else float(db[max(0, i - 1)])
    above = cur > pre_db + 3.0
    hit = np.nonzero(above[:-1] & above[1:])[0]
    return round((a0 + int(hit[0]) * ms) / sr, 3) if len(hit) else round(i * STEP, 3)


def analyze_audio(audio: np.ndarray, sr: int = SR) -> dict:
    """Mảng tiếng → {floor_db, top_db, thr_db, onsets, clusters, quiet, env_db} (xem analyze)."""
    db = envelope(audio, sr)
    n = len(db)
    dur = round(len(audio) / sr, 3)
    if n < 5:
        return {"step": STEP, "duration": dur, "floor_db": -120.0, "top_db": -120.0, "thr_db": -120.0,
                "onsets": [], "clusters": [], "quiet": [], "env_db": [round(float(x), 1) for x in db]}
    floor = max(float(np.percentile(db, 10)), -90.0)   # nền CỦA CHÍNH CLIP (phòng yên, tiếng xe xa, ồn máy)
    top = float(np.percentile(db, 99))
    thr = floor + float(np.clip(0.25 * (top - floor), 6.0, 12.0))

    # mốc bật
    onsets = []
    for i in pick_onsets(onset_strength(db)):
        before = float(db[max(0, i - 3):i].min()) if i > 0 else float(db[0])
        after = float(db[i:min(n, i + 3)].max())
        peak = float(db[i:min(n, i + 6)].max())
        if after - before < ONSET_MIN_RISE or peak < floor + ONSET_ABOVE:
            continue
        onsets.append({"t": _refine(audio, sr, db, i), "db": round(peak, 1), "rise": round(after - before, 1)})

    # cụm tiếng: trên ngưỡng (trễ 3dB khi tắt), nối khe < GAP_MERGE
    on = np.zeros(n, bool)
    act = False
    for i in range(n):
        act = db[i] >= thr if not act else db[i] >= thr - 3.0
        on[i] = act
    spans, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            spans.append([i * STEP, j * STEP])
            i = j
        else:
            i += 1
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] < GAP_MERGE:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    for o in onsets:   # mốc bật nằm ngoài cụm (tiếng rất khẽ, dưới ngưỡng cụm) → cụm nhỏ riêng
        if not any(a - 0.03 <= o["t"] <= b for a, b in merged):
            merged.append([o["t"], o["t"] + 0.05])
    merged.sort()
    clusters = []
    for a, b in merged:
        ons = [o for o in onsets if a - 0.03 <= o["t"] <= b]
        if b - a < MIN_CLUSTER and not ons:
            continue
        a = min(a, ons[0]["t"]) if ons else a
        k0, k1 = int(a / STEP), max(int(a / STEP) + 1, int(round(b / STEP)))
        pk = float(db[k0:k1].max())
        clusters.append({"n": len(clusters) + 1, "t0": round(a, 3), "t1": round(b, 3), "dur": round(b - a, 3),
                         "peak_db": round(pk, 1), "onset": ons[0]["t"] if ons else round(a, 3),
                         "onsets": [o["t"] for o in ons], "kind": "bật gọn" if b - a <= SHORT else "kéo dài"})

    # điểm lặng: chỗ yên nhất (trung bình trượt 30ms) trong từng khe — cả khe đầu (trước cụm 1) và khe cuối
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    edges = [0.0] + [x for c in clusters for x in (c["t0"], c["t1"])] + [n * STEP]
    quiet = []
    for lo, hi in zip(edges[::2], edges[1::2]):
        k0, k1 = int(round(lo / STEP)), int(round(hi / STEP))
        if k1 - k0 < 4:
            continue
        # tìm trong phần khe đã trừ đệm (sau đuôi POST_GUARD, trước tiếng PRE_GUARD) — khe hẹp quá thì cả khe
        g0 = k0 + (int(round(POST_GUARD / STEP)) if lo > 0 else 0)
        g1 = k1 - (int(round(PRE_GUARD / STEP)) if hi < n * STEP else 0)
        if g1 - g0 >= 1:
            k0, k1 = g0, g1
        k = k0 + int(np.argmin(sm[k0:k1]))
        quiet.append({"t": round((k + 0.5) * STEP, 3), "db": round(float(sm[k]), 1), "lo": round(lo, 3), "hi": round(hi, 3)})
    return {"step": STEP, "duration": dur, "floor_db": round(floor, 1), "top_db": round(top, 1), "thr_db": round(thr, 1),
            "onsets": onsets, "clusters": clusters, "quiet": quiet, "env_db": [round(float(x), 1) for x in db]}


def _hash(path: Path) -> str:
    h = hashlib.sha1(f"sound|{VERSION}|{SR}|{STEP}|{ONSET_K}|{ONSET_MIN_RISE}|{ONSET_ABOVE}".encode())
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def analyze(media_path: Path, out_json: Path) -> tuple[dict, bool]:
    """Phân tích (cache theo hash file) → (kết quả, có tính lại không). Định dạng sound/<key>.json:
    {key, version, step 0.01, duration, floor_db (nền p10), top_db (p99), thr_db (ngưỡng cụm),
     onsets [{t, db, rise}], clusters [{n, t0, t1, dur, peak_db, onset, onsets[], kind}], quiet [{t, db, lo, hi}],
     env_db [dB mỗi 10ms]}."""
    key = _hash(media_path)
    if out_json.exists():
        old = json.loads(out_json.read_text(encoding="utf-8"))
        if old.get("key") == key:
            return old, False
    res = {"key": key, "version": VERSION, **analyze_audio(load(media_path))}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return res, True


# ───────────────────────── tra cứu cho cutlib ─────────────────────────
def cluster(info: dict, n: int) -> dict:
    cs = info.get("clusters") or []
    if not 1 <= n <= len(cs):
        raise ValueError(f"không có cụm tiếng #{n} (có {len(cs)} cụm)")
    return cs[n - 1]


def cluster_edge(info: dict, n: int, side: str, pad: float) -> tuple[float, str]:
    """Mép cắt quanh cụm #n: side "in" = trước lúc bật `pad` giây, "out" = sau đuôi `pad` giây — nhưng không lấn sang
    cụm liền trước / liền sau (khe hẹp → điểm lặng của khe đó). Trả (giây, ghi chú)."""
    cs = info.get("clusters") or []
    c = cluster(info, n)
    dur = float(info.get("duration") or c["t1"] + pad)
    if side == "in":
        want, lo, hi = c["t0"] - pad, (cs[n - 2]["t1"] if n >= 2 else 0.0), c["t0"]
        ok = want >= lo + (POST_GUARD if n >= 2 else 0.0)
    else:
        want, lo, hi = c["t1"] + pad, c["t1"], (cs[n]["t0"] if n < len(cs) else dur)
        ok = want <= hi - (PRE_GUARD if n < len(cs) else 0.0)
    if ok:
        return round(min(max(0.0, want), dur), 3), "lặng"
    q = next((q for q in info.get("quiet") or [] if abs(q["lo"] - lo) < 0.02 and abs(q["hi"] - hi) < 0.02), None)
    x = q["t"] if q else (lo + hi) / 2
    return round(min(max(0.0, x), dur), 3), f"khe hẹp {hi - lo:.2f}s → điểm lặng"


def busy(info: dict, t: float) -> dict | None:
    """Cụm tiếng đang kêu ở giây t (tính cả khoảng đệm trước tiếng / sau đuôi) — None = chỗ lặng, cắt được."""
    return next((c for c in info.get("clusters") or [] if c["t0"] - PRE_GUARD < t < c["t1"] + POST_GUARD), None)


def snap(info: dict, t: float, side: str, tol: float = 0.5) -> tuple[float, str]:
    """Bám mép cắt về chỗ lặng gần nhất (không cắt giữa một tiếng). side = "in" (mép vào: ưu tiên lùi về TRƯỚC tiếng
    để giữ trọn tiếng bật) | "out" (mép ra: ưu tiên kéo về SAU đuôi tiếng). Trả (giây, ghi chú):
      "lặng"        mép vốn nằm ở chỗ lặng — giữ nguyên;
      "bám ±x"      đã dời x giây tới chỗ lặng;
      "giữa tiếng"  không có chỗ lặng trong ±tol (tiếng kéo dài: rót, xay) → chỗ nhỏ tiếng nhất quanh mép."""
    dur = float(info.get("duration") or 0.0)
    t = min(max(0.0, t), dur) if dur else max(0.0, t)
    if busy(info, t) is None:
        return round(t, 3), "lặng"
    cs = info.get("clusters") or []
    safe = []   # các khoảng cắt được: khe giữa các cụm (đã trừ đệm), cả đầu và cuối nguồn
    edges = [0.0] + [x for c in cs for x in (c["t0"] - PRE_GUARD, c["t1"] + POST_GUARD)] + [dur]
    for lo, hi in zip(edges[::2], edges[1::2]):
        lo, hi = max(0.0, lo), min(dur, hi) if dur else hi
        if hi > lo:
            safe.append((lo, hi))
    # hướng ưu tiên TUYỆT ĐỐI: mép vào trong tiếng → về trước tiếng (giữ trọn tiếng bật), mép ra → sau đuôi; chỉ khi
    # hướng đó không có chỗ lặng trong ±tol mới dời ngược lại (bỏ cả tiếng) — không cắt nửa tiếng đá / nửa tiếng nắp
    before = [hi for lo, hi in safe if hi <= t and t - hi <= tol + 1e-9]
    after = [lo for lo, hi in safe if lo >= t and lo - t <= tol + 1e-9]
    pref, other = (before, after) if side == "in" else (after, before)
    cand = pref or other
    if cand:
        x = round(min(cand, key=lambda v: abs(v - t)), 3)
        return x, f"bám {x - t:+.2f}s"
    env = np.asarray(info.get("env_db") or [], np.float32)   # tiếng kéo dài: chỗ nhỏ tiếng nhất trong ±min(tol, 0,25s)
    step = float(info.get("step", STEP))
    w = min(tol, 0.25)
    k0, k1 = max(0, int((t - w) / step)), min(len(env), int((t + w) / step) + 1)
    if k1 - k0 < 2:
        return round(t, 3), "giữa tiếng"
    sm = np.convolve(env[k0:k1], np.ones(3) / 3, mode="same")
    return round((k0 + int(np.argmin(sm)) + 0.5) * step, 3), "giữa tiếng"


SETTLE_DROP = 20.0   # dB dưới đỉnh của clip = "đã tắt tiếng" (không thấp hơn nền + 6dB: nguồn ồn thì coi như luôn yên → không dời)
SETTLE_TAIL = 0.03   # giữ thêm 30ms sau chỗ đuôi tắt / trước chỗ tiếng bật


def settle(info: dict, t: float, side: str, limit: float) -> float:
    """Mép đoạn LỜI bám theo TIẾNG THẬT. Mốc từ của Whisper hay kết thúc sớm hơn tiếng (đo 10/11: 'robot' hết ở 24,40s
    theo Whisper, tiếng thật tới 24,57s) → mép ra đặt theo mốc từ cắt cụt đuôi 40–60ms. Nếu ở mép `t` tiếng còn to:
      side="out": kéo mép RA tới chỗ tiếng tắt hẳn + 30ms, không quá `limit` (đầu từ kế / đầu đoạn kế);
      side="in":  lùi mép VÀO về chỗ còn yên − 30ms, không quá `limit` (cuối từ trước / cuối đoạn trước).
    Mép vốn đã yên, hoặc không có chỗ yên trong tầm (nói liền hơi) → giữ nguyên `t`."""
    env = info.get("env_db") or []
    step = float(info.get("step", STEP))
    if not env:
        return t
    quiet = max(float(info["floor_db"]) + 6.0, float(info["top_db"]) - SETTLE_DROP)
    k = min(len(env) - 1, max(0, int(t / step)))
    if env[k] <= quiet:
        return t
    if side == "out":
        for j in range(k + 1, min(len(env), int(limit / step) + 1)):
            if env[j] <= quiet:
                return round(min(limit, j * step + SETTLE_TAIL), 3)
    else:
        for j in range(k - 1, max(-1, int(limit / step) - 1), -1):
            if env[j] <= quiet:
                return round(max(limit, (j + 1) * step - SETTLE_TAIL), 3)
    return t


# ───────────────────────── ảnh soát: dải khung + sóng âm cùng trục ─────────────────────────
STRIP_STEP = 0.5     # 1 khung / 0,5s (ảnh lưới 8 khung quá thưa để chọn điểm cắt ASMR)
CANVAS_W = 1600
MARGIN = 56


def _frames(video: Path, duration: float, tw: int, th: int) -> list[np.ndarray]:
    sdr = media.sdr_filter(video)
    vf = f"fps={1 / STRIP_STEP:.4f},scale={tw}:{th}" + (f",{sdr}" if sdr else "") + ",format=rgb24"
    raw = subprocess.run([config.FFMPEG, "-v", "error", "-ss", f"{STRIP_STEP / 2:.3f}", "-i", str(video), "-an",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    k = len(raw) // (tw * th * 3)
    arr = np.frombuffer(raw[: k * tw * th * 3], np.uint8).reshape(k, th, tw, 3) if k else np.zeros((0, th, tw, 3), np.uint8)
    return list(arr)


def sheet(media_path: Path, info: dict, out: Path, label: str, video: dict | None = None) -> Path:
    """Ảnh soát cho Claude chọn điểm cắt: mỗi hàng ~6s — dải khung 0,5s/khung (ô = khoảng thời gian, khung chụp ở giữa
    ô) + sóng âm dB cùng trục; vạch giây (to mỗi 1s), cụm tiếng tô màu + số #n (cam = bật gọn, xanh = kéo dài),
    vạch đỏ = mốc bật, tam giác xanh lá = điểm lặng (chỗ cắt an toàn), vạch đứt = ngưỡng cụm.
    video = {"width", "height"} nếu nguồn có hình; None = chỉ tiếng (mỗi hàng 10s)."""
    from PIL import Image, ImageDraw, ImageFont
    dur = float(info["duration"])
    inner = CANVAS_W - 2 * MARGIN
    if video:
        portrait = video["height"] >= video["width"]
        th = 210 if portrait else 130
        tw = int(round(th * video["width"] / video["height"] / 2)) * 2
        per_row = max(4, inner // tw) * STRIP_STEP
    else:
        th = tw = 0
        per_row = 10.0
    frames = _frames(media_path, dur, tw, th) if video else []
    px = inner / per_row                       # điểm ảnh / giây
    wave_h, ruler_h, gap = 120, 26, 14
    row_h = th + wave_h + ruler_h + gap
    rows = max(1, int(np.ceil(dur / per_row - 1e-6)))
    head = 64
    W, H = CANVAS_W, head + rows * row_h + 10
    im = Image.new("RGB", (W, H), (20, 20, 24))
    dr = ImageDraw.Draw(im, "RGBA")
    f_b = ImageFont.truetype(str(config.FONT_BOLD), 22)
    f_s = ImageFont.truetype(str(config.FONT_REGULAR), 15)
    f_n = ImageFont.truetype(str(config.FONT_BOLD), 15)
    cs, ons, qs = info.get("clusters") or [], info.get("onsets") or [], info.get("quiet") or []
    n_short = sum(c["kind"] == "bật gọn" for c in cs)
    dr.text((MARGIN, 10), f"{label} · {dur:.2f}s · nền {info['floor_db']:.0f} dB · ngưỡng cụm {info['thr_db']:.0f} dB · "
            f"{len(cs)} cụm ({n_short} bật gọn, {len(cs) - n_short} kéo dài) · {len(ons)} mốc bật", fill=(240, 240, 240), font=f_b)
    dr.text((MARGIN, 38), "cam = bật gọn · xanh = kéo dài · đỏ = mốc bật · tam giác xanh lá = điểm lặng (cắt an toàn) · "
            "vạch đứt = ngưỡng cụm · ô khung = 0,5s, chụp giữa ô", fill=(160, 160, 170), font=f_s)
    env = np.asarray(info.get("env_db") or [], np.float32)
    step = float(info.get("step", STEP))
    lo_db = float(info["floor_db"]) - 6
    hi_db = max(float(info["top_db"]) + 3, lo_db + 20)
    for r in range(rows):
        r0, r1 = r * per_row, min(dur, (r + 1) * per_row)
        y0 = head + r * row_h
        x_of = lambda t: MARGIN + (t - r0) * px   # noqa: E731
        # dải khung
        for k in range(int(round(r0 / STRIP_STEP)), int(np.ceil(r1 / STRIP_STEP - 1e-6))):
            if k < len(frames):
                im.paste(Image.fromarray(frames[k]), (int(x_of(k * STRIP_STEP)), y0))
        wy = y0 + th
        dr.rectangle((MARGIN, wy, x_of(r1), wy + wave_h), fill=(30, 30, 38))
        for c in cs:   # cụm tiếng (dưới sóng)
            a, b = max(c["t0"], r0), min(c["t1"], r1)
            if b <= a:
                continue
            col = (255, 150, 40, 70) if c["kind"] == "bật gọn" else (70, 150, 255, 70)
            dr.rectangle((x_of(a), wy, x_of(b), wy + wave_h), fill=col)
            if c["t0"] >= r0 - 1e-6:
                dr.text((x_of(c["t0"]) + 3, wy + 3), f"#{c['n']}", fill=(255, 235, 120), font=f_n)
        # sóng âm (dB từ nền → đỉnh)
        k0, k1 = int(r0 / step), min(len(env), int(np.ceil(r1 / step)))
        base = wy + wave_h - 2
        for x in range(int(x_of(r0)), int(x_of(r1))):
            t_a, t_b = r0 + (x - MARGIN) / px, r0 + (x + 1 - MARGIN) / px
            ka, kb = max(k0, int(t_a / step)), min(k1, max(int(t_a / step) + 1, int(np.ceil(t_b / step))))
            if kb <= ka:
                continue
            v = (float(env[ka:kb].max()) - lo_db) / (hi_db - lo_db)
            hh = int(np.clip(v, 0, 1) * (wave_h - 20))
            dr.line((x, base, x, base - hh), fill=(150, 200, 255))
        ty = base - int(np.clip((float(info["thr_db"]) - lo_db) / (hi_db - lo_db), 0, 1) * (wave_h - 20))
        for x in range(MARGIN, int(x_of(r1)), 12):
            dr.line((x, ty, min(x + 6, int(x_of(r1))), ty), fill=(200, 200, 200, 150))
        for o in ons:   # mốc bật: vạch đỏ xuyên sóng + nhô lên đáy dải khung
            if r0 <= o["t"] < r1:
                x = x_of(o["t"])
                dr.line((x, wy - (16 if th else 0), x, wy + wave_h), fill=(255, 60, 60), width=2)
        for q in qs:   # điểm lặng
            if r0 <= q["t"] < r1:
                x = x_of(q["t"])
                dr.polygon([(x - 6, wy + wave_h - 1), (x + 6, wy + wave_h - 1), (x, wy + wave_h - 12)], fill=(80, 230, 120))
        # thước giây
        ry = wy + wave_h
        t = np.ceil(r0 * 10 - 1e-6) / 10
        while t <= r1 + 1e-6:
            x = x_of(t)
            tenth = int(round(t * 10))
            major, half = tenth % 10 == 0, tenth % 5 == 0
            dr.line((x, ry, x, ry + (12 if major else 7 if half else 3)), fill=(220, 220, 220) if major else (140, 140, 150))
            if major or half:
                dr.text((x + 2, ry + 5), f"{tenth // 10}s" if major else f"{t:.1f}", fill=(240, 240, 240) if major else (150, 150, 160),
                        font=f_n if major else f_s)
                if major and th:   # vạch giây mảnh xuyên dải khung
                    dr.line((x, y0, x, y0 + th), fill=(255, 255, 0, 70))
            t = round(t + 0.1, 3)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=88)
    return out
