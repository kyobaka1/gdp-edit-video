"""Chép lời tiếng Việt có mốc TỪNG TỪ bằng Whisper chạy local trên GPU (faster-whisper / CTranslate2).

Sếp duyệt 05/11 (ngoại lệ luật "không chạy model nặng local"): chữ động hiện theo từng từ cần mốc ±50ms, Gemini chỉ cho
mốc câu. Model tải 1 lần về cache HuggingFace (~3GB), card RTX 4060 8GB chạy float16. Không có GPU → CPU int8 (chậm).
Kết quả cache theo (hash file + model + gợi ý) trong thư mục job, chạy lại không tốn gì.
"""

import hashlib
import json
import os
import site
import sys
import time
import wave
from pathlib import Path

import numpy as np

from studio import config, media

MODEL = os.getenv("EDIT_ASR_MODEL", "").strip() or "large-v3"
_model = None


def _cuda_dlls() -> None:
    """Windows: cuBLAS/cuDNN cài bằng pip (nvidia-*-cu12) nằm trong site-packages/nvidia/*/bin — đưa vào PATH."""
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        for sub in ("cublas", "cudnn", "cuda_nvrtc"):
            d = Path(sp) / "nvidia" / sub / "bin"
            if d.is_dir() and str(d) not in os.environ["PATH"]:
                os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]
                os.add_dll_directory(str(d))


def model():
    global _model
    if _model is None:
        _cuda_dlls()
        from faster_whisper import WhisperModel
        try:
            _model = WhisperModel(MODEL, device="cuda", compute_type="float16")
            _model.device_used = "cuda"
        except Exception as exc:  # không có GPU / thiếu DLL → CPU (chậm ~10×) nhưng vẫn ra kết quả
            print(f"  ⚠ Whisper không chạy được GPU ({type(exc).__name__}: {str(exc)[:120]}) → chạy CPU int8")
            _model = WhisperModel(MODEL, device="cpu", compute_type="int8")
            _model.device_used = "cpu"
    return _model


def _hash(path: Path, extra: str) -> str:
    h = hashlib.sha1(extra.encode("utf-8"))
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# Câu Whisper hay bịa trên tiếng nền/nhạc (thấy 05/11 trên clip vlog: "Hãy subscribe cho kênh La La School…",
# "Cảm ơn các bạn đã theo dõi và hẹn gặp lại.", "Hẹn gặp lại các bạn trong những video tiếp theo.")
_HALLU = ("subscribe", "đăng ký kênh", "theo dõi và hẹn gặp lại", "cảm ơn các bạn đã theo dõi",
          "hẹn gặp lại các bạn trong", "video tiếp theo", "la la school", "ghiền mì gõ", "like và share")


def _hallucination(seg, ws) -> str:
    low = seg.text.lower()
    hit = next((h for h in _HALLU if h in low), None)
    if hit:
        return f"câu bịa quen thuộc ('{hit}')"
    if seg.no_speech_prob > 0.6 and seg.avg_logprob < -0.6:
        return f"không có lời (no_speech {seg.no_speech_prob:.2f}, logprob {seg.avg_logprob:.2f})"
    if ws and sum(w.probability for w in ws) / len(ws) < 0.35:
        return f"xác suất từ thấp ({sum(w.probability for w in ws) / len(ws):.2f})"
    if seg.compression_ratio > 2.6:
        return f"lặp chữ (compression {seg.compression_ratio:.1f})"
    return ""


def _tighten(words: list[dict], audio: np.ndarray, sr: int = 16000) -> list[dict]:
    """Whisper gán khoảng lặng TRƯỚC một từ vào chính từ đó (đo 05/11: "Tôi" 2,86–3,40s nhưng tiếng thật bắt đầu ~3,3s)
    → chữ hiện sớm. Kéo đầu/cuối từ về chỗ năng lượng tiếng thật (RMS 10ms vượt ngưỡng theo mức lời quanh đó)."""
    for p0, p1 in pauses(audio, sr):
        for i, w in enumerate(words):
            # từ "bắt đầu" ngay trước/trong khoảng lặng → tiếng thật của nó nằm SAU khoảng lặng
            if p0 - 0.12 <= w["start"] < p1 and w["end"] > p0 + 0.05:
                w["start"] = round(p1, 3)
                w["end"] = round(max(w["end"], p1 + 0.12), 3)
                for v in words[i + 1:]:  # đẩy các từ sau nếu bị chồng
                    if v["start"] >= words[i]["end"] - 0.02:
                        break
                    v["start"] = round(words[i]["end"], 3)
                    v["end"] = round(max(v["end"], v["start"] + 0.08), 3)
            # từ "kết thúc" trong khoảng lặng → cắt về đầu khoảng lặng
            elif w["start"] < p0 < w["end"] <= p1 + 0.05:
                w["end"] = round(p0 + 0.04, 3)
    return words


def pauses(audio: np.ndarray, sr: int = 16000, min_len: float = 0.15) -> list[tuple[float, float]]:
    """Khoảng lặng thật (≥ min_len giây): RMS 10ms dưới ngưỡng = mức lời to (p95) − 30 dB, sàn −50 dBFS."""
    hop = sr // 100
    n = len(audio) // hop
    if n == 0:
        return []
    db = 20 * np.log10(np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    thr = max(float(np.percentile(db, 95)) - 30, -50)
    quiet = db < thr
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) / 100 >= min_len:
                out.append((i / 100, j / 100))
            i = j
        else:
            i += 1
    return out


_PUNCT = ".,!?;:…\"'“”()[]"


def norm(tok: str) -> str:
    """So khớp chữ: thường hoá, bỏ dấu câu, GIỮ dấu thanh (tiện ≠ tiền)."""
    return tok.lower().strip(_PUNCT + " ")


def correct(words: list[dict], reference: str, trust: bool = True) -> tuple[list[dict], list[dict]]:
    """Giữ MỐC của Whisper, lấy CHỮ đúng từ văn bản chuẩn (kịch bản TTS, hoặc bản Gemini chép lại giọng thật).
    Đo 05/11: Whisper sai ~2% từ ("tính tiền lợi", "danh thu", "phổ Coffee") — Gemini chép đúng hết.
    Trả (words mới, danh sách chỗ đã sửa để in cho người soát). Mỗi từ thêm `punct` = dấu câu theo sau (gợi ý ngắt khối).
    trust=False (văn bản chuẩn là Gemini NGHE lại giọng thật, không phải kịch bản): chỗ Gemini thêm nhiều từ mà Whisper
    không nghe ra thì KHÔNG dồn chữ vào khe thời gian giả — giữ Whisper, ghi "nghe tay" (05/11, clip đám đông c01:
    Gemini thêm "Xin chào tất cả mọi người" vào 0,28s đầu)."""
    import difflib
    ref = [t for t in reference.split() if t.strip(_PUNCT)]
    a, b = [norm(w["w"]) for w in words], [norm(t) for t in ref]
    out, changes = [], []

    def mk(tok: str, s: float, e: float, p: float = 1.0) -> dict:
        core = tok.strip(_PUNCT)
        lead = tok[: len(tok) - len(tok.lstrip(_PUNCT))]
        return {"w": core, "start": round(s, 3), "end": round(e, 3), "p": p,
                "punct": tok[len(lead) + len(core):].strip()}

    for op, i0, i1, j0, j1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            out += [mk(ref[j0 + k], words[i0 + k]["start"], words[i0 + k]["end"], words[i0 + k]["p"]) for k in range(i1 - i0)]
        elif op == "replace" and not trust and abs((j1 - j0) - (i1 - i0)) > 1:
            out += [dict(w, punct="") for w in words[i0:i1]]
            changes.append({"at": round(words[i0]["start"], 2), "asr": " ".join(w["w"] for w in words[i0:i1]),
                            "ref": " ".join(ref[j0:j1]), "note": "lệch nhiều từ — giữ Whisper, nghe tay"})
        elif op == "insert" and not trust:
            changes.append({"at": round(out[-1]["end"] if out else 0.0, 2), "asr": "", "ref": " ".join(ref[j0:j1]),
                            "note": "Whisper không nghe ra — bỏ qua, nghe tay"})
        elif op == "replace":
            s, e = words[i0]["start"], words[i1 - 1]["end"]
            if i1 - i0 == j1 - j0:   # thay 1:1 → giữ mốc từng từ
                new = [mk(ref[j0 + k], words[i0 + k]["start"], words[i0 + k]["end"]) for k in range(i1 - i0)]
            else:                     # khác số từ → chia khoảng thời gian theo độ dài chữ
                lens = [max(1, len(norm(ref[j]))) for j in range(j0, j1)]
                tot, acc, new = sum(lens), 0, []
                for j, ln in zip(range(j0, j1), lens):
                    new.append(mk(ref[j], s + (e - s) * acc / tot, s + (e - s) * (acc + ln) / tot))
                    acc += ln
            out += new
            changes.append({"at": round(s, 2), "asr": " ".join(w["w"] for w in words[i0:i1]),
                            "ref": " ".join(ref[j0:j1])})
        elif op == "insert":          # chữ chuẩn Whisper không nghe ra → chen vào khe giữa 2 từ
            s = out[-1]["end"] if out else (words[i0]["start"] if i0 < len(words) else 0.0)
            e = words[i0]["start"] if i0 < len(words) else s + 0.25 * (j1 - j0)
            e = max(e, s + 0.12 * (j1 - j0))
            for k, j in enumerate(range(j0, j1)):
                out.append(mk(ref[j], s + (e - s) * k / (j1 - j0), s + (e - s) * (k + 1) / (j1 - j0), 0.0))
            changes.append({"at": round(s, 2), "asr": "", "ref": " ".join(ref[j0:j1])})
        else:                         # Whisper nghe thừa (tiếng đệm / bịa) → bỏ
            changes.append({"at": round(words[i0]["start"], 2), "asr": " ".join(w["w"] for w in words[i0:i1]), "ref": ""})
    return out, changes


def transcribe(media_path: Path, out_json: Path, hint: str = "") -> dict:
    """→ {"words": [{w, start, end, p}], "text", "speech": giây có lời, "duration", "model"}.
    hint = tên riêng / thuật ngữ trong PLAN (brand, địa danh) để Whisper viết đúng chính tả."""
    key = _hash(media_path, f"{MODEL}|{hint}")
    if out_json.exists():
        old = json.loads(out_json.read_text(encoding="utf-8"))
        if old.get("key") == key:
            return old
    wav = out_json.with_suffix(".wav")
    media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(media_path), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    # tự đọc WAV → mảng float32: decode_audio của faster-whisper 1.2.1 gọi av.open(metadata_errors=…) mà PyAV 19 đã bỏ
    with wave.open(str(wav)) as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768.0
    t0 = time.time()
    m = model()
    segs, info = m.transcribe(audio, language="vi", word_timestamps=True, beam_size=5,
                              vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
                              condition_on_previous_text=False,
                              initial_prompt=hint or None)
    words, texts, dropped = [], [], []
    for s in segs:
        ws = [w for w in (s.words or []) if w.word.strip()]
        why = _hallucination(s, ws)
        if why:  # đoạn tiếng nền / nhạc mà Whisper "nghe" ra câu bịa → bỏ, ghi lại để soát
            dropped.append({"text": s.text.strip(), "start": round(s.start, 2), "end": round(s.end, 2), "why": why})
            continue
        texts.append(s.text.strip())
        for w in ws:
            words.append({"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "p": round(w.probability, 3)})
    words = _tighten(words, audio)
    wav.unlink(missing_ok=True)
    speech = sum(w["end"] - w["start"] for w in words)
    res = {"key": key, "model": MODEL, "device": getattr(m, "device_used", "?"), "seconds": round(time.time() - t0, 1),
           "duration": round(info.duration, 3), "speech": round(speech, 2), "text": " ".join(texts), "words": words,
           "dropped": dropped}
    out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
