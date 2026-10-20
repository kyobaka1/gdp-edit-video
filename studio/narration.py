"""Thuyết minh tiếng Việt LIỀN MẠCH: một kịch bản nhiều đoạn → đọc trong MỘT lần TTS (một giọng, một tông)
→ Gemini định vị từng đoạn trong audio → cắt tại chỗ ngắt nghỉ → đặt mỗi đoạn vào cảnh của nó (`at`).

Sếp 20/10: không đọc từng câu phụ đề (rời rạc, đổi tông 3–4 lần); thuyết minh phải bám nội dung video, có câu
chuyển tiếp. Cổng kiểm ngược bắt buộc (TTS từng tự bịa "khoan bê tông", "miễn phí vận chuyển").
"""

import hashlib
import json
import wave
from pathlib import Path

import numpy as np
from google.genai import types

from studio import config, gemini
from studio.voice import TTS_MODEL, _match, _save_audio, spoken

ALIGN_SCHEMA = {
    "type": "object",
    "properties": {"paragraphs": {"type": "array", "items": {"type": "object", "properties": {
        "index": {"type": "integer"}, "start": {"type": "number"}, "end": {"type": "number"},
    }, "required": ["index", "start", "end"]}}},
    "required": ["paragraphs"],
}
GAP = 0.15  # khoảng nghỉ tối thiểu giữa 2 đoạn khi phải dời


def _read(p: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(p)) as w:
        rate, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return (a.reshape(-1, ch).mean(axis=1) if ch > 1 else a), rate


def _write(p: Path, a: np.ndarray, rate: int) -> None:
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def _quietest(a: np.ndarray, rate: int, t: float, radius: float = 0.35) -> int:
    """Mẫu im nhất (RMS khung 20ms) trong ±radius quanh t — chỗ cắt an toàn giữa 2 đoạn."""
    hop = int(rate * 0.02)
    lo, hi = max(0, int((t - radius) * rate)), min(len(a) - hop, int((t + radius) * rate))
    if hi <= lo:
        return int(t * rate)
    starts = range(lo, hi, hop)
    rms = [float(np.sqrt(np.mean(a[s:s + hop] ** 2))) for s in starts]
    return list(starts)[int(np.argmin(rms))] + hop // 2


def _pauses(a: np.ndarray, rate: int, min_len: float = 0.12) -> list[tuple[float, float]]:
    """Các khoảng lặng thật trong lượt đọc: [(giữa, độ dài)] — ứng viên điểm cắt giữa 2 đoạn."""
    hop = int(rate * 0.02)
    rms = np.array([np.sqrt(np.mean(a[s:s + hop] ** 2)) for s in range(0, len(a) - hop, hop)])
    voiced = rms[rms > 0.01]
    thr = max(0.006, 0.08 * float(np.median(voiced))) if len(voiced) else 0.006
    out, run = [], None
    for k, quiet in enumerate(rms < thr):
        if quiet and run is None:
            run = k
        elif not quiet and run is not None:
            length = (k - run) * 0.02
            if length >= min_len:
                out.append(((run + k) / 2 * 0.02, length))
            run = None
    return out


def _hear(path: Path) -> str:
    return gemini.client().models.generate_content(model=config.GEMINI_MODEL, contents=[
        types.Part.from_bytes(data=path.read_bytes(), mime_type="audio/wav"),
        "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."]).text or ""


def _trim(a: np.ndarray, rate: int, thr: float = 0.008) -> np.ndarray:
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a[:0]
    pad = int(rate * 0.04)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def _tts(text: str, voice: str, out: Path) -> str:
    resp = gemini.client().models.generate_content(
        model=TTS_MODEL, contents=text,  # KHÔNG kèm chỉ dẫn giọng điệu (model sẽ đọc tiếp/bịa)
        config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
    part = resp.candidates[0].content.parts[0]
    _save_audio(part.inline_data.data, part.inline_data.mime_type, out)
    return gemini.client().models.generate_content(model=config.GEMINI_MODEL, contents=[
        types.Part.from_bytes(data=out.read_bytes(), mime_type="audio/wav"),
        "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."]).text or ""


def build(job_dir: Path, retries: int = 3) -> dict:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((job_dir / "edl.json").read_text(encoding="utf-8"))
    nar = edl.get("narration") or {}
    paras = [p for p in nar.get("paragraphs", []) if (p.get("text") or "").strip()]
    if not paras:
        raise ValueError("edl.json chưa có narration.paragraphs")
    voice = nar.get("voice", "Kore")
    # chữ GỬI TTS (tên brand đã đổi sang cách đọc chuẩn); mọi bước kiểm ngược so với bản này
    said = [spoken(p["text"].strip()) for p in paras]
    full = "\n\n".join(said)
    work = job_dir / "narration"
    work.mkdir(exist_ok=True)
    key = hashlib.sha1(f"{TTS_MODEL}|{voice}|{full}".encode()).hexdigest()[:12]
    raw = work / f"take_{key}.wav"
    usage = job_dir / "usage.jsonl"

    # 1) Một lượt đọc cả bài + cổng kiểm ngược (cache theo nội dung)
    take_meta = raw.with_suffix(".json")
    if not (raw.exists() and take_meta.exists()):
        last = ""
        for attempt in range(1, retries + 1):
            heard = _tts(full, voice, raw)
            score = _match(full, heard)
            with usage.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"label": f"narration[{key}]#{attempt}", "model": TTS_MODEL, "match": round(score, 3)}) + "\n")
            if score >= 0.9:
                take_meta.write_text(json.dumps({"heard": heard.strip(), "match": round(score, 3)}, ensure_ascii=False, indent=2), encoding="utf-8")
                break
            last = heard.strip()
            raw.unlink(missing_ok=True)
        else:
            raise RuntimeError(f"TTS không khớp kịch bản sau {retries} lần. Nghe ra: {last[:300]!r}")
    a, rate = _read(raw)

    # 2) Định vị từng đoạn trong audio
    listing = "\n".join(f"{i}: {s}" for i, s in enumerate(said))
    al = gemini.generate_json([
        types.Part.from_bytes(data=raw.read_bytes(), mime_type="audio/wav"),
        "Audio là giọng đọc lần lượt các đoạn dưới đây. Cho mỗi đoạn, trả thời điểm BẮT ĐẦU và KẾT THÚC "
        "(giây, số thập phân, tính từ đầu audio).\n" + listing], ALIGN_SCHEMA, usage_log=usage, label="narration_align")
    spans = {s["index"]: (s["start"], s["end"]) for s in al["paragraphs"]}
    if sorted(spans) != list(range(len(paras))):
        raise RuntimeError(f"Định vị đoạn thiếu/thừa: {sorted(spans)}")

    # 3) Chọn điểm cắt: ranh giới Gemini báo chỉ là ước lượng (đo 20/10: lệch tới 1 cụm từ). Quanh ước lượng
    #    lấy các khoảng lặng thật, ưu tiên khoảng DÀI nhất (ngắt đoạn dài hơn ngắt dấu phẩy), nghe lại mảnh
    #    vừa cắt — khớp đoạn của nó thì nhận, không thì thử ứng viên kế.
    pauses = _pauses(a, rate)
    cuts = [0]
    for i in range(1, len(paras)):
        est = (spans[i - 1][1] + spans[i][0]) / 2
        prev_t = cuts[-1] / rate
        cands = sorted([p for p in pauses if prev_t + 0.5 < p[0] and abs(p[0] - est) <= 1.6],
                       key=lambda p: (-p[1], abs(p[0] - est)))[:4]
        best_cut, best_score = _quietest(a, rate, est), -1.0
        for mid, _ in cands:
            cut = int(mid * rate)
            probe = work / "probe.wav"
            _write(probe, _trim(a[cuts[-1]:cut], rate), rate)
            score = _match(said[i - 1], _hear(probe))
            if score > best_score:
                best_cut, best_score = cut, score
            if score >= 0.9:
                break
        cuts.append(best_cut)
    cuts.append(len(a))
    dur = meta["duration"]
    timeline = np.zeros(int(dur * rate), dtype=np.float32)
    placed, warnings, cursor = [], [], 0.0
    for i, p in enumerate(paras):
        piece = _trim(a[cuts[i]:cuts[i + 1]], rate)
        start = max(float(p["at"]), cursor + (GAP if i else 0.0))
        end = start + len(piece) / rate
        drift = start - float(p["at"])
        if drift > 0.8:
            warnings.append(f"đoạn {i} vào trễ {drift:.1f}s so với cảnh (at={p['at']}) — rút đoạn {i - 1} hoặc lùi at")
        s0 = int(start * rate)
        seg = piece[: max(0, len(timeline) - s0)]
        timeline[s0:s0 + len(seg)] += seg
        if end > dur - 0.1:
            warnings.append(f"đoạn {i} tràn quá cuối video {end - dur + 0.1:.1f}s — rút kịch bản")
        placed.append({"index": i, "at": p["at"], "start": round(start, 3), "end": round(end, 3),
                       "drift": round(drift, 2), "text": p["text"].strip(), "said": said[i]})
        cursor = end
    # 4) Cổng kiểm từng mảnh: nghe lại → phải khớp đúng đoạn của nó (bắt lỗi định vị/cắt dính sang đoạn bên)
    for i, pl in enumerate(placed):
        piece_path = work / f"piece_{i:02}.wav"
        _write(piece_path, _trim(a[cuts[i]:cuts[i + 1]], rate), rate)
        heard = _hear(piece_path)
        pl["heard"], pl["match"] = heard.strip(), round(_match(pl["said"], heard), 3)
        if pl["match"] < 0.8:
            warnings.append(f"mảnh {i} cắt lệch (khớp {pl['match']}): nghe ra {heard.strip()[:80]!r}")
    out = job_dir / "narration.wav"
    _write(out, timeline, rate)
    report = {"voice": voice, "model": TTS_MODEL, "take": raw.name, "take_seconds": round(len(a) / rate, 2),
              "match": json.loads(take_meta.read_text(encoding="utf-8"))["match"], "pieces": placed,
              "warnings": warnings}
    (job_dir / "narration.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
