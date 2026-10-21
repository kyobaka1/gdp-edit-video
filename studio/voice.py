"""Giọng đọc tiếng Việt (Gemini TTS) + nhạc nền (Lyria) cho một job.

Mỗi câu TTS phải qua CỔNG KIỂM NGƯỢC: Gemini nghe lại → chữ phải khớp câu gốc. Lý do: thử 20/10, TTS từng
tự chèn thêm câu "Miễn phí vận chuyển…" — tuyên bố quảng cáo không được phép lọt vào video.
"""

import base64
import hashlib
import json
import re
import struct
import time
import unicodedata
import wave
from difflib import SequenceMatcher
from pathlib import Path

import requests
from google.genai import types

from studio import config, gemini, media

# Đo 20/10 (tools/probe_tts_literal.py): kèm câu chỉ dẫn giọng điệu là model "nhập vai" và ĐỌC TIẾP
# (3.8-flash-tts tự thêm "…dùng khoan bê tông…" vào câu "Đánh dấu vị trí bằng bút."). Gửi ĐÚNG câu,
# không chỉ dẫn → cả 3 model đọc nguyên văn; 3.1-flash-tts-preview ổn định nhất (khớp 1,00 mọi kiểu).
TTS_MODEL = "gemini-3.1-flash-tts-preview"
# Chuỗi dự phòng (Sếp 21/10): TTS_MODEL chỉ 100 request/24h → hết quota (429) thì nhảy sang model kế.
# Model hết quota được nhớ trong tiến trình, các câu sau đi thẳng model kế. Lỗi khác (5xx, mạng) chỉ bỏ
# qua model đó cho LƯỢT gọi này. Mọi model vẫn phải qua cổng kiểm ngược như cũ.
TTS_CHAIN = [
    ("gemini", TTS_MODEL),
    ("gemini", "gemini-3.8-flash-tts"),
    ("tokenrouter", "openai/gpt-audio-mini"),  # chat completions + audio ra; cần lời dặn "đọc nguyên văn"
    ("tokenrouter", "openai/gpt-audio"),
]
TOKENROUTER_URL = "https://api.tokenrouter.com/v1/chat/completions"
# Giọng OpenAI khi shop.json voice không khai `openai` (gpt-audio không có giọng prebuilt của Gemini)
OPENAI_VOICE_BY_GENDER = {"nữ": "coral", "nam": "ash"}
_READ_VERBATIM = ("Bạn là máy đọc văn bản tiếng Việt. Đọc to NGUYÊN VĂN đoạn người dùng gửi, không thêm, "
                  "không bớt, không trả lời, không bình luận.")
_exhausted: set[str] = set()
MUSIC_MODEL = "lyria-3.5"
MAX_TEMPO = 1.35  # ép nhanh tối đa; vượt nữa giọng méo → phải rút câu
_TIMESTAMP = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")  # bước nghe lại đôi khi chèn "00:00" đầu câu


_LEXICON: list[tuple[re.Pattern, str]] | None = None


def spoken(text: str) -> str:
    """Thay tên brand bằng cách đọc Sếp chốt (assets/pronunciation.json) trước khi gửi TTS.
    TTS tự đọc PHALEDO thành "Fa-li-đô" → sai; Sếp chốt "Pha lê đô" (20/10)."""
    global _LEXICON
    if _LEXICON is None:
        p = config.ROOT / "assets" / "pronunciation.json"
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        items = sorted(((k, v) for k, v in data.items() if not k.startswith("_")), key=lambda kv: -len(kv[0]))
        _LEXICON = [(re.compile(rf"(?<!\w){re.escape(k)}(?!\w)", re.IGNORECASE), v) for k, v in items]
    for pat, rep in _LEXICON:
        text = pat.sub(rep, text)
    return text


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
        # gpt-audio trả WAV kiểu luồng: ô kích thước = 0xFFFFFFFF → wave đọc ra 89.478s. Lấy PCM sau chunk
        # "data" + thông số chunk "fmt " rồi ghi lại header đúng.
        if struct.unpack("<I", data[4:8])[0] == 0xFFFFFFFF:
            fmt = data.index(b"fmt ") + 8
            ch, rate, bits = struct.unpack("<HI", data[fmt + 2:fmt + 8]) + struct.unpack("<H", data[fmt + 14:fmt + 16])
            pcm = data[data.index(b"data") + 8:]
            with wave.open(str(out), "wb") as w:
                w.setnchannels(ch)
                w.setsampwidth(bits // 8)
                w.setframerate(rate)
                w.writeframes(pcm[: len(pcm) // (ch * bits // 8) * (ch * bits // 8)])
            return
        out.write_bytes(data)
        return
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)


def _classify(exc: Exception) -> str:
    """'wait' = giới hạn theo PHÚT (đợi rồi thử lại cùng model) · 'dead' = hết quota ngày / hết tiền / bị chặn
    (bỏ model cho cả lượt chạy) · 'error' = lỗi khác (chỉ bỏ qua lượt gọi này)."""
    resp = getattr(exc, "response", None)
    code = getattr(exc, "code", None) or getattr(resp, "status_code", None)
    msg = str(exc) + (getattr(resp, "text", "") or "")
    if code == 429 and ("PerMinute" in msg or "within 1 minutes" in msg):  # Gemini RPM · tokenrouter 5 req/phút
        return "wait"
    if code in (402, 403, 429) or "RESOURCE_EXHAUSTED" in msg:
        # 403: tokenrouter trả "violation of provider Terms Of Service" cho openai/gpt-audio (đo 21/10, mọi câu)
        return "dead"
    return "error"


def _gemini_tts(model: str, text: str, voice: dict) -> tuple[bytes, str]:
    resp = gemini.client().models.generate_content(
        model=model, contents=text,  # KHÔNG kèm chỉ dẫn giọng điệu (model sẽ đọc tiếp/bịa)
        config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice["name"])))))
    part = resp.candidates[0].content.parts[0]
    return part.inline_data.data, part.inline_data.mime_type


def _tokenrouter_tts(model: str, text: str, voice: dict) -> tuple[bytes, str]:
    if not config.TOKENROUTER_API_KEY:
        raise RuntimeError("Thiếu TOKENROUTER_API_KEY trong .env")
    ov = voice.get("openai") or OPENAI_VOICE_BY_GENDER.get(voice.get("gender", ""), "coral")
    r = requests.post(TOKENROUTER_URL, timeout=300, headers={"Authorization": f"Bearer {config.TOKENROUTER_API_KEY}"},
                      json={"model": model, "modalities": ["text", "audio"], "audio": {"voice": ov, "format": "wav"},
                            "messages": [{"role": "system", "content": _READ_VERBATIM},
                                         {"role": "user", "content": text}]})
    r.raise_for_status()
    audio = (r.json()["choices"][0]["message"].get("audio") or {}).get("data")
    if not audio:
        raise RuntimeError(f"{model} không trả audio")
    return base64.b64decode(audio), "audio/wav"


def synthesize(text: str, voice: dict, out: Path, usage: Path | None = None,
               chain: list[tuple[str, str]] | None = None) -> str:
    """TTS `text` ra `out` (WAV) theo TTS_CHAIN, trả tên model đã dùng. `voice` = shop.json voice
    ({name: giọng Gemini, gender, openai?: giọng gpt-audio}). Hết cả chuỗi → lỗi kèm lý do từng model."""
    errors = []
    for provider, model in chain or TTS_CHAIN:
        call = _gemini_tts if provider == "gemini" else _tokenrouter_tts
        for attempt in range(3):  # chỉ lặp khi bị giới hạn theo phút
            if model in _exhausted:
                break
            try:
                data, mime = call(model, text, voice)
            except Exception as exc:
                kind = _classify(exc)
                if kind == "dead":
                    _exhausted.add(model)
                errors.append(f"{model}: {kind.upper()} {type(exc).__name__} {str(exc)[:160]}")
                if usage is not None:
                    with usage.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"label": "tts_fallback", "model": model, "error": errors[-1]}, ensure_ascii=False) + "\n")
                if kind == "wait" and attempt < 2:
                    time.sleep(61)
                    continue
                break
            _save_audio(data, mime, out)
            return model
    raise RuntimeError("Mọi model TTS đều lỗi:\n  " + "\n  ".join(errors or ["(cả chuỗi đã hết quota trong lượt chạy này)"]))


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
        raw = out_dir / f"raw_{key}.wav"
        used = synthesize(text, {"name": voice, "gender": gender}, raw, usage)
        heard = gemini.client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=raw.read_bytes(), mime_type="audio/wav"),
                      "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."],
        ).text or ""
        score = _match(text, heard)
        with usage.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"label": f"tts[{key}]#{attempt}", "model": used, "match": round(score, 3)}) + "\n")
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
