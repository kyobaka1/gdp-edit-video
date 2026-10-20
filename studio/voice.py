"""Giọng đọc tiếng Việt (Gemini TTS) + nhạc nền (Lyria) cho một job.

Mỗi câu TTS phải qua CỔNG KIỂM NGƯỢC: Gemini nghe lại → chữ phải khớp câu gốc. Lý do: thử 20/10, TTS từng
tự chèn thêm câu "Miễn phí vận chuyển…" — tuyên bố quảng cáo không được phép lọt vào video.
"""

import hashlib
import json
import re
import unicodedata
import wave
from difflib import SequenceMatcher
from pathlib import Path

from google.genai import types

from studio import config, gemini, media

# Đo 20/10 (tools/probe_tts_literal.py): kèm câu chỉ dẫn giọng điệu là model "nhập vai" và ĐỌC TIẾP
# (3.8-flash-tts tự thêm "…dùng khoan bê tông…" vào câu "Đánh dấu vị trí bằng bút."). Gửi ĐÚNG câu,
# không chỉ dẫn → cả 3 model đọc nguyên văn; 3.1-flash-tts-preview ổn định nhất (khớp 1,00 mọi kiểu).
TTS_MODEL = "gemini-3.1-flash-tts-preview"
MUSIC_MODEL = "lyria-3.5"
MAX_TEMPO = 1.35  # ép nhanh tối đa; vượt nữa giọng méo → phải rút câu
_TIMESTAMP = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")  # bước nghe lại đôi khi chèn "00:00" đầu câu


def _norm(s: str) -> str:
    s = _TIMESTAMP.sub(" ", unicodedata.normalize("NFC", s)).lower()
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def _match(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _wav_duration(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def _save_audio(data: bytes, mime: str, out: Path) -> None:
    if data[:4] == b"RIFF":
        out.write_bytes(data)
        return
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)


def tts_line(text: str, voice: str, gender: str, out_dir: Path, usage: Path, retries: int = 3) -> dict:
    """TTS 1 câu + kiểm ngược + cắt lặng đầu/cuối. Cache theo hash (đổi câu mới tốn token)."""
    key = hashlib.sha1(f"{TTS_MODEL}|{voice}|{gender}|{text}".encode()).hexdigest()[:12]
    final = out_dir / f"vo_{key}.wav"
    meta_p = final.with_suffix(".json")
    if final.exists() and meta_p.exists():
        return json.loads(meta_p.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    last = ""
    for attempt in range(1, retries + 1):
        resp = gemini.client().models.generate_content(
            model=TTS_MODEL,
            contents=text,  # KHÔNG kèm chỉ dẫn (xem ghi chú TTS_MODEL)
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))),
        )
        part = resp.candidates[0].content.parts[0]
        raw = out_dir / f"raw_{key}.wav"
        _save_audio(part.inline_data.data, part.inline_data.mime_type, raw)
        heard = gemini.client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=raw.read_bytes(), mime_type="audio/wav"),
                      "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."],
        ).text or ""
        score = _match(text, heard)
        with usage.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"label": f"tts[{key}]#{attempt}", "model": TTS_MODEL, "match": round(score, 3)}) + "\n")
        if score >= 0.85:
            # cắt lặng đầu/cuối (giữ lặng giữa câu), 24k mono → 48k stereo cho ghép
            media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(raw), "-af",
                       "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
                       "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
                       "-ar", "48000", "-ac", "2", str(final)])
            raw.unlink(missing_ok=True)
            info = {"text": text, "file": final.name, "duration": round(_wav_duration(final), 3),
                    "heard": heard.strip(), "match": round(score, 3), "attempts": attempt}
            meta_p.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            return info
        last = heard.strip()
    raise RuntimeError(f"TTS không khớp sau {retries} lần — câu: {text!r} · nghe ra: {last!r}")


def build(job_dir: Path) -> dict:
    """Sinh giọng đọc cho edl['voiceover'], tính tempo để vừa khung. Ghi voice.json. Câu quá dài → lỗi kèm gợi ý."""
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((job_dir / "edl.json").read_text(encoding="utf-8"))
    vo = edl.get("voiceover") or {}
    lines = [ln for ln in vo.get("lines", []) if (ln.get("text") or "").strip()]
    if not lines:
        raise ValueError("edl.json chưa có voiceover.lines")
    voice, gender = vo.get("voice", "Kore"), vo.get("gender", "nữ")
    usage = job_dir / "usage.jsonl"
    lines = sorted(lines, key=lambda ln: ln["start"])
    out, too_long = [], []
    for i, ln in enumerate(lines):
        info = tts_line(ln["text"].strip(), voice, gender, job_dir / "voice", usage)
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else meta["duration"]
        slot = max(0.3, nxt - ln["start"] - 0.12)  # chừa 0,12s thở giữa 2 câu
        tempo = max(1.0, info["duration"] / slot)
        if tempo > MAX_TEMPO:
            too_long.append(f"{ln['start']:.2f}s \"{ln['text']}\": đọc {info['duration']:.2f}s, khung {slot:.2f}s "
                            f"(cần nhanh {tempo:.2f}× > {MAX_TEMPO}×) → rút câu")
        out.append({**info, "start": ln["start"], "slot": round(slot, 3), "tempo": round(min(tempo, MAX_TEMPO), 3)})
    report = {"voice": voice, "lines": out, "too_long": too_long}
    (job_dir / "voice.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def make_music(job_dir: Path, prompt: str | None = None) -> Path:
    """Tạo nhạc nền không lời bằng Lyria, dài ≥ video. Ghi jobs/<id>/music.mp3."""
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    secs = int(meta["duration"]) + 5
    prompt = prompt or (f"Instrumental background music for a {secs}-second product video. Upbeat, clean, light "
                        "electronic pop, about 110 BPM, positive tidy feeling, no vocals, no lyrics, steady energy "
                        "suitable under a voiceover, soft ending.")
    resp = gemini.client().models.generate_content(
        model=MUSIC_MODEL, contents=prompt, config=types.GenerateContentConfig(response_modalities=["AUDIO"]))
    for part in resp.candidates[0].content.parts:
        if part.inline_data:
            out = job_dir / "music.mp3"
            out.write_bytes(part.inline_data.data)
            return out
    raise RuntimeError("Lyria không trả audio")
