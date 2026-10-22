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

from studio import config, gemini, outro
from studio.templates import shop_voice
from studio.voice import TTS_MODEL, HearUnavailable, _match, gemini_dead, hear, spoken, synthesize

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
    return hear(path)  # Gemini → tokenrouter gpt-audio-mini khi Gemini hết tiền (voice.hear)


def _spans_by_length(a: np.ndarray, rate: int, said: list[str]) -> dict[int, tuple[float, float]]:
    """Mốc từng đoạn khi không có Gemini định vị: chia khoảng có tiếng theo số ký tự (bỏ dấu cách) mỗi đoạn."""
    voiced = np.where(np.abs(a) > 0.008)[0]
    t0, t1 = (voiced[0] / rate, voiced[-1] / rate) if len(voiced) else (0.0, len(a) / rate)
    w = [max(1, len(s.replace(" ", ""))) for s in said]
    edges = np.concatenate([[0], np.cumsum(w)]) / sum(w) * (t1 - t0) + t0
    return {i: (float(edges[i]), float(edges[i + 1])) for i in range(len(said))}


def _trim(a: np.ndarray, rate: int, thr: float = 0.008) -> np.ndarray:
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a[:0]
    pad = int(rate * 0.04)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def _tts(text: str, voice: dict, out: Path, usage: Path | None = None) -> tuple[str, str]:
    """TTS theo chuỗi dự phòng (voice.TTS_CHAIN) rồi nghe lại. Trả (chữ nghe ra, model đã dùng)."""
    used = synthesize(text, voice, out, usage)
    return _hear(out), used


def build(job_dir: Path, retries: int = 3) -> dict:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((job_dir / "edl.json").read_text(encoding="utf-8"))
    nar = edl.get("narration") or {}
    paras = [p for p in nar.get("paragraphs", []) if (p.get("text") or "").strip()]
    if not paras:
        raise ValueError("edl.json chưa có narration.paragraphs")
    # giọng: edl.narration.voice (ép tay) → giọng của shop (shop.json voice) → Kore
    sv = shop_voice(edl["shop"]) if edl.get("shop") else None
    voice = nar.get("voice") or (sv or {}).get("name") or "Kore"
    # giọng cho model dự phòng gpt-audio: edl.narration.voice_openai → shop.json voice.openai → theo giới tính
    vspec = {"name": voice, "gender": (sv or {}).get("gender", "nữ"),
             "openai": nar.get("voice_openai") or (sv or {}).get("openai")}
    # chữ GỬI TTS (tên brand đã đổi sang cách đọc chuẩn); mọi bước kiểm ngược so với bản này
    said = [spoken(p["text"].strip()) for p in paras]
    full = "\n\n".join(said)
    work = job_dir / "narration"
    work.mkdir(exist_ok=True)
    # khoá cache giữ TTS_MODEL (model chính) dù lượt đọc do model dự phòng làm → take cũ vẫn dùng lại được
    key = hashlib.sha1(f"{TTS_MODEL}|{voice}|{full}".encode()).hexdigest()[:12]
    raw = work / f"take_{key}.wav"
    usage = job_dir / "usage.jsonl"

    # 1) Một lượt đọc cả bài + cổng kiểm ngược (cache theo nội dung)
    take_meta = raw.with_suffix(".json")
    if not (raw.exists() and take_meta.exists()):
        last = ""
        for attempt in range(1, retries + 1):
            heard, used = _tts(full, vspec, raw, usage)
            score = _match(full, heard)
            with usage.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"label": f"narration[{key}]#{attempt}", "model": used, "match": round(score, 3)}) + "\n")
            if score >= 0.9:
                take_meta.write_text(json.dumps({"heard": heard.strip(), "match": round(score, 3), "model": used},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
                break
            last = heard.strip()
            raw.unlink(missing_ok=True)
        else:
            raise RuntimeError(f"TTS không khớp kịch bản sau {retries} lần. Nghe ra: {last[:300]!r}")
    a, rate = _read(raw)

    # 2) Định vị từng đoạn trong audio
    listing = "\n".join(f"{i}: {s}" for i, s in enumerate(said))
    align, radius = "gemini", 1.6
    try:
        if gemini_dead():
            raise RuntimeError("Gemini hết tiền/bị chặn trong lượt này")
        al = gemini.generate_json([
            types.Part.from_bytes(data=raw.read_bytes(), mime_type="audio/wav"),
            "Audio là giọng đọc lần lượt các đoạn dưới đây. Cho mỗi đoạn, trả thời điểm BẮT ĐẦU và KẾT THÚC "
            "(giây, số thập phân, tính từ đầu audio).\n" + listing], ALIGN_SCHEMA, usage_log=usage, label="narration_align")
        spans = {s["index"]: (s["start"], s["end"]) for s in al["paragraphs"]}
        if sorted(spans) != list(range(len(paras))):
            raise RuntimeError(f"Định vị đoạn thiếu/thừa: {sorted(spans)}")
    except Exception as exc:
        # Dự phòng (22/10, Gemini 402): chia thời lượng phần có tiếng theo số chữ từng đoạn → mốc ước lượng thô hơn,
        # nên nới vùng tìm khoảng lặng; bước 3 vẫn nghe lại từng mảnh để chọn điểm cắt, bước 4 vẫn là cổng.
        align, radius = f"ước theo độ dài chữ ({str(exc)[:80]})", 2.5
        spans = _spans_by_length(a, rate, said)

    # 3) Chọn điểm cắt: ranh giới Gemini báo chỉ là ước lượng (đo 20/10: lệch tới 1 cụm từ). Quanh ước lượng
    #    lấy các khoảng lặng thật, ưu tiên khoảng DÀI nhất (ngắt đoạn dài hơn ngắt dấu phẩy), nghe lại mảnh
    #    vừa cắt — khớp đoạn của nó thì nhận, không thì thử ứng viên kế.
    pauses = _pauses(a, rate)
    cuts = [0]
    for i in range(1, len(paras)):
        est = (spans[i - 1][1] + spans[i][0]) / 2
        prev_t = cuts[-1] / rate
        cands = sorted([p for p in pauses if prev_t + 0.5 < p[0] and abs(p[0] - est) <= radius],
                       key=lambda p: (-p[1], abs(p[0] - est)))[:4]
        best_cut, best_score = _quietest(a, rate, est), -1.0
        for mid, _ in cands:
            cut = int(mid * rate)
            probe = work / "probe.wav"
            _write(probe, _trim(a[cuts[-1]:cut], rate), rate)
            try:
                score = _match(said[i - 1], _hear(probe))
            except HearUnavailable:  # dự phòng không nghe được → chưa biết, giữ thứ tự khoảng lặng dài nhất
                score = -0.5
            if score > best_score:
                best_cut, best_score = cut, score
            if score >= 0.9:
                break
        cuts.append(best_cut)
    cuts.append(len(a))
    dur = outro.total_duration(edl, meta)  # thuyết minh được phép chạy sang outro (câu chốt brand trên màn kết)
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
        try:
            heard = _hear(piece_path)
        except HearUnavailable as exc:
            pl["heard"], pl["match"] = "", None
            warnings.append(f"mảnh {i} CHƯA KIỂM được ({str(exc)[:70]}) — nghe tay trước khi giao")
            continue
        pl["heard"], pl["match"] = heard.strip(), round(_match(pl["said"], heard), 3)
        if pl["match"] < 0.8:
            warnings.append(f"mảnh {i} cắt lệch (khớp {pl['match']}): nghe ra {heard.strip()[:80]!r}")
    out = job_dir / "narration.wav"
    _write(out, timeline, rate)
    tm = json.loads(take_meta.read_text(encoding="utf-8"))
    used = tm.get("model", TTS_MODEL)  # take cũ (trước 21/10) không ghi model = model chính
    if used != TTS_MODEL:
        warnings.append(f"lượt đọc do model DỰ PHÒNG {used} làm (model chính hết quota/lỗi) — nghe lại giọng trước khi giao")
    report = {"voice": voice, "model": used, "align": align,
              "take": raw.name, "take_seconds": round(len(a) / rate, 2), "match": tm["match"], "pieces": placed,
              "warnings": warnings}
    (job_dir / "narration.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
