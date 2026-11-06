r"""Tổng hợp tiếng hiệu ứng cho Scene Library bằng code (tất định, không tải gì) → assets/sfx/scene/*.wav (48 kHz mono).

    .\.venv\Scripts\python.exe tools\make_scene_sfx.py

GDP (giấy, dứt khoát): paper_whoosh · PHALEDO Dark (kính, mềm): soft_swell, glass_ting · PHALEDO Warm (sổ tay): page_slide.
Dùng kèm 2 tiếng Kenney CC0 có sẵn (impactSoft "thịch", click "tách"). Mức trộn đặt trong scene.json (gain_db, đỉnh).
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parents[1] / "assets" / "sfx" / "scene"
rng = np.random.default_rng(20261105)


def noise(sec):
    return rng.standard_normal(int(SR * sec)).astype(np.float32)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] *= 0.02
    return np.fft.irfft(X, len(x)).astype(np.float32)


def env(n, attack, release, shape=2.0):
    t = np.linspace(0, 1, n, dtype=np.float32)
    a = np.clip(t / max(attack, 1e-4), 0, 1) ** shape
    r = np.clip((1 - t) / max(release, 1e-4), 0, 1) ** shape
    return a * r


def sweep_filter(x, f0, f1):
    """Lọc dải trượt tần (tiếng vút): chia khúc, mỗi khúc một dải."""
    out = np.zeros_like(x)
    k = 24
    seg = len(x) // k
    for i in range(k):
        c = f0 * (f1 / f0) ** (i / (k - 1))
        s = bandpass(x[i * seg:(i + 1) * seg + 512], c * 0.6, c * 1.6)[:seg]
        out[i * seg:i * seg + len(s)] = s
    return out


def norm(x, peak_db=-3.0):
    return (x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)).astype(np.float32)


def save(name, x):
    OUT.mkdir(parents=True, exist_ok=True)
    x = norm(x)
    k = int(SR * 0.004)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print(f"{OUT / name}.wav  {len(x) / SR:.2f}s")


# giấy vút: nhiễu lọc dải trượt 900→5000 Hz + lạo xạo (xung thưa) — 0,34s
n = noise(0.34)
w = sweep_filter(n, 900, 5000) * env(len(n), 0.35, 0.55)
crk = np.zeros_like(n)
idx = rng.choice(len(n), 60, replace=False)
crk[idx] = rng.uniform(-1, 1, 60)
crk = bandpass(crk, 2500, 9000) * env(len(n), 0.2, 0.7) * 3.0
save("paper_whoosh", w + crk)

# ánh sáng dâng nhẹ: nhiễu trầm lọc thấp + hoà âm mềm (La3 + Mi4) phồng lên rồi tắt — 0,9s
t = np.arange(int(SR * 0.9)) / SR
pad = (np.sin(2 * np.pi * 220 * t) + 0.6 * np.sin(2 * np.pi * 329.6 * t) + 0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
air = bandpass(noise(0.9), 200, 2500) * 0.35
save("soft_swell", (pad * 0.5 + air) * env(len(t), 0.55, 0.45, 1.6))

# tiếng kính "ting": các bội âm không chẵn (Đô7, Sol7…) tắt dần nhanh chậm khác nhau — 1,3s
t = np.arange(int(SR * 1.3)) / SR
parts = [(2093.0, 1.0, 3.2), (3135.9, 0.55, 4.5), (4186.0, 0.35, 6.0), (5274.0, 0.18, 8.0), (2637.0, 0.25, 3.8)]
ting = sum(a * np.sin(2 * np.pi * f * t + i) * np.exp(-d * t) for i, (f, a, d) in enumerate(parts)).astype(np.float32)
ting *= np.clip(t / 0.003, 0, 1).astype(np.float32)
save("glass_ting", ting)

# giấy trượt: nhiễu lọc cao có rung ma sát (điều biên 38 Hz) — 0,42s
n = noise(0.42)
t = np.arange(len(n)) / SR
fr = (0.75 + 0.25 * np.sin(2 * np.pi * 38 * t)).astype(np.float32)
save("page_slide", bandpass(n, 1800, 7500) * fr * env(len(n), 0.25, 0.6, 1.4))

# ── Keyword Burst (C01) ──
# GDP "vút" ngắn khi từ khoá bật (mẫu M2: tiếng vút tần cao ở từ khoá): nhiễu trượt 1500→7000 Hz + nhịp trầm rất nhẹ — 0,24s
n = noise(0.24)
t = np.arange(len(n)) / SR
thump = (np.sin(2 * np.pi * (90 - 40 * t / t[-1]) * t) * np.exp(-t * 38)).astype(np.float32)
save("word_whoosh", sweep_filter(n, 1500, 7000) * env(len(n), 0.3, 0.55) + 0.35 * thump)

# PHALEDO Dark: hơi kính lấp lánh — nhiễu cao dâng + 2 bội âm mảnh (La6, Mi7) — 0,6s
t = np.arange(int(SR * 0.6)) / SR
air = bandpass(noise(0.6), 3500, 11000) * 0.6
glint = (0.5 * np.sin(2 * np.pi * 1760 * t) + 0.3 * np.sin(2 * np.pi * 2637 * t)).astype(np.float32) * np.exp(-t * 5).astype(np.float32)
save("air_shimmer", (air + glint * np.clip(t / 0.18, 0, 1).astype(np.float32)) * env(len(t), 0.4, 0.5, 1.5))

# PHALEDO Warm: bút chì gạch chân — nhiễu cao, 3 nét đưa tay (điều biên không đều) — 0,36s
n = noise(0.36)
t = np.arange(len(n)) / SR
strokes = np.clip(np.sin(2 * np.pi * 8.5 * t + 0.6) * 0.8 + 0.35, 0, 1).astype(np.float32)
save("pencil_scribble", bandpass(n, 2200, 8000) * strokes * env(len(n), 0.08, 0.3, 1.2))
sys.exit(0)
