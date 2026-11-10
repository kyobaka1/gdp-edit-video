"""Kiểm thử dựng video KHÔNG LỜI theo tiếng động (studio/edit/sound.py + cutlib c.sound / cap(at=) / auto_caps):

  1  MỐC BẬT trên tiếng tổng hợp có đáp án (nắp bật, đá chạm ly, đá rơi giữa lúc rót, gõ rất khẽ ~20dB trên nền, kéo nắp):
     bắt đủ (hụt 0), không báo nhầm, sai số ≤ 10ms trung bình / ≤ 20ms lớn nhất.
  2  NGƯỠNG TƯƠNG ĐỐI: cả bản nhỏ đi 20dB (máy thu xa) → vẫn ra đúng các mốc đó (silencedetect −35dB sẽ mất gần hết).
  3  CỤM + ĐIỂM LẶNG: đúng số cụm, đúng kiểu bật gọn / kéo dài, điểm lặng nằm ngoài mọi cụm.
  4  BÁM MÉP: mép rơi giữa tiếng → dời về chỗ lặng (vào: lùi trước tiếng · ra: sau đuôi); tiếng kéo dài → "giữa tiếng".
  5  c.sound(): không tự rút khoảng lặng (1 đoạn liền), ghi fade_ms 30, mép đã bám; cap(at=giây / "key#n") ra khối chữ.
  6  auto_caps(): gom từ theo dấu câu / lặng ≥ 0,3s / ≤ max_words, khối khớp lời, job không gọi auto_caps không đổi.

Chạy: .\\.venv\\Scripts\\python.exe tools\\test_sound.py          (không gọi API, không cần GPU)
      .\\.venv\\Scripts\\python.exe tools\\test_sound.py --write a.wav   (ghi tiếng tổng hợp 48kHz để ghép vào clip thử)
"""

import json
import shutil
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.edit import sound  # noqa: E402

ok = bad = 0


def check(cond: bool, msg: str) -> None:
    global ok, bad
    ok, bad = ok + bool(cond), bad + (not cond)
    print(f"  [{'ĐẠT' if cond else 'CHƯA ĐẠT'}] {msg}")


# ───────────────────────── tiếng tổng hợp có đáp án ─────────────────────────
def synth(sr: int = 16000, gain_db: float = 0.0, seed: int = 7, floor_db: float = -60.0) -> tuple[np.ndarray, list[float], list[tuple]]:
    """→ (tiếng, mốc bật đúng, cụm đúng [(t0, t1 xấp xỉ, kiểu)]). Nền ồn trắng floor_db dBFS (mặc định −60),
    floor_db > −60: nền ồn dao động chậm ±3dB (quạt, xe xa) — kiểm báo nhầm."""
    rng = np.random.default_rng(seed)
    T = 14.0
    n = int(T * sr)
    a = rng.standard_normal(n).astype(np.float32) * 10 ** (floor_db / 20)
    if floor_db > -60:
        a *= (10 ** (3 * np.sin(2 * np.pi * 0.4 * np.arange(n) / sr) / 20)).astype(np.float32)
    t = np.arange(n) / sr

    def burst(at, amp, tau, length):          # nắp bật / gõ: ồn tắt dần nhanh
        k0, k = int(at * sr), int(length * sr)
        env = np.exp(-np.arange(k) / sr / tau)
        a[k0:k0 + k] += (rng.standard_normal(k) * env * amp).astype(np.float32)

    def clink(at, amp, tau=0.06, length=0.3):  # đá chạm ly: 2 sóng sin tắt dần
        k0, k = int(at * sr), int(length * sr)
        tt = np.arange(k) / sr
        a[k0:k0 + k] += (amp * np.exp(-tt / tau) * (np.sin(2 * np.pi * 2700 * tt) + 0.6 * np.sin(2 * np.pi * 4100 * tt))
                         ).astype(np.float32)

    def flow(t0, t1, rms_db, attack, release, am_db=2.0):   # rót nước / kéo nắp: ồn kéo dài, vào/ra mềm
        k0, k1 = int(t0 * sr), int(t1 * sr)
        x = rng.standard_normal(k1 - k0)
        x = np.convolve(x, np.ones(4) / 4, mode="same")          # bớt chói
        x = x / np.sqrt((x ** 2).mean()) * 10 ** (rms_db / 20)
        tt = np.arange(k1 - k0) / sr
        env = np.minimum(1.0, tt / attack) * np.minimum(1.0, (tt[-1] - tt) / release)
        env *= 10 ** (am_db * np.sin(2 * np.pi * 2.5 * tt) / 20)
        a[k0:k1] += (x * env).astype(np.float32)

    burst(1.0, 0.25, 0.015, 0.08)       # nắp bật
    clink(2.3, 0.12)                    # đá chạm ly
    clink(2.75, 0.08)                   # chạm lần 2
    flow(4.0, 7.5, -26, 0.06, 0.15)     # rót nước 3,5s
    clink(5.2, 0.2)                     # đá rơi vào ly GIỮA lúc rót
    burst(9.0, 0.012, 0.012, 0.06)      # gõ rất khẽ (~−38dBFS đỉnh, ~20dB trên nền)
    clink(10.5, 0.1)
    flow(12.0, 12.8, -30, 0.02, 0.1)    # kéo nắp
    del t
    truth_on = [1.0, 2.3, 2.75, 4.0, 5.2, 9.0, 10.5, 12.0]
    truth_cl = [(1.0, 1.08, "bật gọn"), (2.3, 2.5, "bật gọn"), (2.75, 2.95, "bật gọn"), (4.0, 7.5, "kéo dài"),
                (9.0, 9.06, "bật gọn"), (10.5, 10.7, "bật gọn"), (12.0, 12.8, "kéo dài")]
    return a * 10 ** (gain_db / 20), truth_on, truth_cl


def score(found: list[float], truth: list[float], tol: float = 0.03) -> tuple[list[float], list[float], list[float]]:
    errs, used, miss = [], set(), []
    for x in truth:
        k = min(range(len(found)), key=lambda i: abs(found[i] - x), default=None)
        if k is None or abs(found[k] - x) > tol or k in used:
            miss.append(x)
        else:
            used.add(k)
            errs.append(found[k] - x)
    extra = [f for i, f in enumerate(found) if i not in used]
    return errs, miss, extra


def write_wav(path: Path, a: np.ndarray, sr: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


if len(sys.argv) > 2 and sys.argv[1] == "--write":
    a, on, cl = synth(48000)
    write_wav(Path(sys.argv[2]), a, 48000)
    print(f"ghi {sys.argv[2]} · mốc bật đúng {on}")
    sys.exit(0)

infos = {}
for name, g in (("gốc", 0.0), ("nhỏ đi 20dB", -20.0)):
    print(f"== {'1 mốc bật' if g == 0 else '2 ngưỡng tương đối'} ({name})")
    a, truth, truth_cl = synth(gain_db=g)
    info = sound.analyze_audio(a)
    infos[name] = info
    found = [o["t"] for o in info["onsets"]]
    errs, miss, extra = score(found, truth)
    ms = [abs(e) * 1000 for e in errs]
    print(f"     nền {info['floor_db']} dB · ngưỡng cụm {info['thr_db']} dB · mốc tìm được {found}")
    check(not miss, f"bắt đủ {len(truth) - len(miss)}/{len(truth)} mốc" + (f" (hụt {miss})" if miss else ""))
    check(not extra, f"báo nhầm {len(extra)}" + (f" ({extra})" if extra else ""))
    if ms:
        check(np.mean(ms) <= 10 and max(ms) <= 20,
              f"sai số TB {np.mean(ms):.1f}ms · lớn nhất {max(ms):.1f}ms (cần ≤10 / ≤20) · từng mốc "
              + ", ".join(f"{e * 1000:+.0f}" for e in errs))
    if g == 0:
        print("== 3 cụm + điểm lặng")
        cs = info["clusters"]
        print("     " + " · ".join(f"#{c['n']} {c['t0']:.2f}–{c['t1']:.2f} {c['kind']}" for c in cs))
        check(len(cs) == len(truth_cl), f"{len(cs)} cụm (đúng {len(truth_cl)})")
        if len(cs) == len(truth_cl):
            check(all(abs(c["t0"] - t0) <= 0.03 for c, (t0, _, _) in zip(cs, truth_cl)), "đầu cụm lệch ≤ 30ms")
            check(all(c["kind"] == k for c, (_, _, k) in zip(cs, truth_cl)), "đúng kiểu bật gọn / kéo dài")
            long_ = cs[3]
            check(abs(long_["t1"] - 7.5) <= 0.12 and 5.2 in [round(x, 1) for x in long_["onsets"]],
                  f"cụm rót {long_['t0']:.2f}–{long_['t1']:.2f}s chứa mốc đá rơi 5,2s")
        qs = info["quiet"]
        check(len(qs) >= len(cs) - 1 and all(sound.busy(info, q["t"]) is None or q["t"] in (0, info["duration"])
                                               for q in qs if q["hi"] - q["lo"] > 0.2),
              f"{len(qs)} điểm lặng, nằm ngoài mọi cụm")
cmp = [round(o["t"], 2) for o in infos["gốc"]["onsets"]] == [round(o["t"], 2) for o in infos["nhỏ đi 20dB"]["onsets"]]
check(cmp, "bản nhỏ đi 20dB ra cùng mốc bật với bản gốc")
print("== 2b nền ồn −45dB dao động ±3dB (quạt / xe xa): tiếng gõ khẽ chìm trong nền là đúng, không được báo nhầm")
a, truth, _ = synth(floor_db=-45.0)
inf_n = sound.analyze_audio(a)
errs, miss, extra = score([o["t"] for o in inf_n["onsets"]], [t for t in truth if t != 9.0])
print(f"     nền {inf_n['floor_db']} dB · mốc {[o['t'] for o in inf_n['onsets']]}")
check(not miss and not extra, f"bắt {len(truth) - 1 - len(miss)}/{len(truth) - 1} mốc nổi trên nền, báo nhầm {len(extra)}"
      + (f" (hụt {miss}, nhầm {extra})" if miss or extra else ""))

print("== 4 bám mép")
info = infos["gốc"]
x, why = sound.snap(info, 2.35, "in")
check(x <= 2.3 - sound.PRE_GUARD + 1e-6 and why.startswith("bám"), f"mép vào 2,35s (giữa tiếng đá) → {x}s ({why})")
x, why = sound.snap(info, 2.35, "out")
check(2.45 <= x <= 2.75 - sound.PRE_GUARD and why.startswith("bám"), f"mép ra 2,35s → {x}s sau đuôi tiếng ({why})")
x, why = sound.snap(info, 3.5, "in")
check(x == 3.5 and why == "lặng", f"mép 3,5s ở chỗ lặng giữ nguyên ({why})")
x, why = sound.snap(info, 6.0, "out")
check(why == "giữa tiếng" and 5.75 <= x <= 6.25, f"mép 6,0s giữa tiếng rót 3,5s → {x}s ({why}, chỗ nhỏ tiếng nhất ±0,25s)")

print("== 4b mép LỜI bám tiếng thật (sound.settle) — Whisper báo hết từ sớm hơn tiếng")
sr = 16000
rng = np.random.default_rng(3)
talk = rng.normal(0, 10 ** (-70 / 20), 4 * sr).astype(np.float32)
for a_, b_ in ((0.5, 1.26), (1.9, 2.5), (2.5, 3.2)):   # từ 1 (đuôi tắt 1,26s) · từ 2 + từ 3 nói LIỀN (không có lặng ở 2,5s)
    talk[int(a_ * sr):int(b_ * sr)] += rng.normal(0, 10 ** (-14 / 20), int(b_ * sr) - int(a_ * sr)).astype(np.float32)
tinfo = sound.analyze_audio(talk, sr)
x = sound.settle(tinfo, 1.20, "out", 1.9)
check(1.26 <= x <= 1.32, f"mép ra 1,20s (tiếng còn to tới 1,26s) → {x}s = đuôi tắt + 30ms")
check(sound.settle(tinfo, 1.50, "out", 1.9) == 1.50, "mép ra 1,50s đã ở chỗ lặng → giữ nguyên")
check(sound.settle(tinfo, 2.50, "out", 2.7) == 2.50, "mép 2,50s giữa hai từ nói liền (không có chỗ yên trong tầm) → giữ nguyên")
x = sound.settle(tinfo, 1.95, "in", 1.4)
check(1.84 <= x <= 1.90, f"mép vào 1,95s (tiếng đã bật từ 1,90s) → {x}s = trước tiếng 30ms")
check(sound.settle(tinfo, 1.20, "out", 1.22) == 1.20, "giới hạn là đầu từ kế 1,22s (chưa tắt tiếng trước đó) → giữ nguyên, không lấn từ kế")

# ───────────────────────── cutlib trên job giả ─────────────────────────
from studio.edit import cutlib  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="test_sound_"))
try:
    (tmp / "sound").mkdir()
    (tmp / "asr").mkdir()
    (tmp / "meta.json").write_text(json.dumps({"id": "t", "kind": "edit", "out": {"w": 1080, "h": 1920, "fps": 30}}),
                                   encoding="utf-8")
    (tmp / "sound" / "c01.json").write_text(json.dumps(info), encoding="utf-8")
    words = [("Hôm", 0.50), ("nay", 0.72), ("mình", 0.95), ("pha", 1.18), ("cà", 1.40), ("phê,", 1.62),
             ("đá", 1.85), ("thật", 2.05), ("nhiều.", 2.25), ("Rất", 3.10), ("ngon", 3.32), ("và", 3.55),
             ("mát", 3.78), ("lạnh.", 4.0)]
    ws = []
    for w, s in words:
        core = w.strip(".,")
        ws.append({"w": core, "start": s, "end": round(s + 0.2, 3), "p": 0.9, "punct": w[len(core):]})
    (tmp / "asr" / "vo.json").write_text(json.dumps({"words": ws}, ensure_ascii=False), encoding="utf-8")
    (tmp / "sources.json").write_text(json.dumps({
        "c01": {"file": "sources/c01.mp4", "duration": 14.0, "has_audio": True, "has_video": True, "width": 720,
                "height": 1280, "fps": 30.0, "speech": 0, "sound": {"file": "sound/c01.json"}},
        "c02": {"file": "sources/c02.mp4", "duration": 14.0, "has_audio": True, "has_video": True, "width": 720,
                "height": 1280, "fps": 30.0, "speech": 3.0, "words_file": "asr/vo.json"}}), encoding="utf-8")
    print("== 5 c.sound() + chữ đặt theo giây / mốc tiếng")
    c = cutlib.Cut(str(tmp / "cut.py"))
    c.sound("c01", 0.5, 3.2)             # lặng giữa 2 tiếng KHÔNG bị rút
    c.sound("c01", "#4", "#4")           # trọn cụm rót
    c.sound("c01", 10.55, 11.5)          # mép vào giữa tiếng đá → lùi về trước tiếng
    c.cap("!ĐÁ VIÊN", at="c01#2", until=2.6)
    c.cap(".rót / !CÀ PHÊ", at="c01#4", until="c01#4")
    e = c.save()
    ps = e["pieces"]
    check(len(ps) == 3 and all(p.get("fade_ms") == 30 for p in ps), "3 đoạn, mỗi đoạn fade_ms 30 (không rút lặng)")
    check(abs(ps[1]["in"] - (4.0 - 0.08)) < 0.03 and abs(ps[1]["out"] - 7.5) < 0.2,
          f"'#4' → trọn cụm rót {ps[1]['in']}–{ps[1]['out']}s")
    check(ps[2]["in"] <= 10.5 - sound.PRE_GUARD + 1e-6, f"mép vào 10,55s giữa tiếng đá → {ps[2]['in']}s")
    b1, b2 = e["captions"]
    check(abs(b1["first"] - 1.8) < 0.06 and 2.4 <= b1["end"] <= 2.6,
          f"cap(at='c01#2', until=2.6) hiện {b1['first']}s (đá chạm 2,30s nguồn = 1,80s bản dựng) tới {b1['end']}s")
    check(abs(b2["first"] - ps[1]["t0"] - 0.08) < 0.06 and b2["end"] > b2["first"] + 2.5,
          f"cap(at='c01#4', until='c01#4') {b2['first']}–{b2['end']}s theo cụm rót")
    check(all(not w["spoken"] for ln in b1["lines"] for w in ln["words"]) and not e["warnings"],
          "chữ không lời không bị cảnh báo 'không có trong lời'")

    print("== 6 auto_caps()")
    c = cutlib.Cut(str(tmp / "cut.py"))
    c.say("c02", 0.4, 4.3, tighten=None)
    c.auto_caps(keys=["cà phê"])
    e = c.save()
    mk = [b["markup"] for b in e["captions"]]
    print("     " + " | ".join(mk))
    check(len(mk) == 3 and mk[0].startswith("hôm nay mình pha") and "!CÀ PHÊ" in mk[0],
          "khối 1 hết ở dấu phẩy, cụm khoá 'cà phê' → dòng `!CÀ PHÊ`")
    check(mk[1] == "đá thật nhiều" and mk[2].startswith("rất ngon"), "ngắt ở dấu chấm + lặng 0,65s")
    check(all(w["spoken"] for b in e["captions"] for ln in b["lines"] for w in ln["words"]), "mọi chữ là lời đã nói")
    old = cutlib.Cut(str(tmp / "cut.py"))
    old.say("c02", 0.4, 4.3)
    old.cap("hôm nay mình / !PHA CÀ PHÊ")
    e_old = old.save()
    check(all("fade_ms" not in p for p in e_old["pieces"]) and len(e_old["captions"]) == 1,
          "job cũ (say + cap tay, không auto_caps): pieces không có fade_ms, chỉ khối viết tay")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\nTỔNG: {ok}/{ok + bad} đạt — {'ĐẠT' if not bad else 'CHƯA ĐẠT'}")
sys.exit(1 if bad else 0)
