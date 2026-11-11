"""Giọng đọc tiếng Việt (tts.vclip.io — Sếp 11/11; dự phòng gpt-audio-mini) + nhạc nền (Lyria) cho một job.

Mỗi câu TTS phải qua CỔNG KIỂM NGƯỢC: nghe lại (Gemini → tokenrouter) → chữ phải khớp câu gốc. Lý do: thử 20/10, TTS từng
tự chèn thêm câu "Miễn phí vận chuyển…" — tuyên bố quảng cáo không được phép lọt vào video.
"""

import base64
import hashlib
import json
import re
import struct
import tempfile
import time
import unicodedata
import wave
from difflib import SequenceMatcher
from pathlib import Path

import requests
from google.genai import types

from studio import config, gemini, media

# Sếp 11/11: TTS chính = tts.vclip.io (giọng clone riêng của Sếp, shop.json voice.vclip) — KHÔNG dùng Gemini
# key để tạo giọng nữa. Đo 11/11: đọc nguyên văn (khớp 0,98), ~3s cho cả bài, trả WAV 48 kHz mono + SRT mốc
# từng khối (khối = 1 đoạn, đoạn dài bị tách theo câu) → narration cắt đoạn theo SRT, không cần Gemini định vị.
TTS_MODEL = "vclip"
# Chuỗi dự phòng: vclip lỗi → tokenrouter gpt-audio-mini (giọng khác hẳn → narrate cảnh báo nghe lại).
# Gemini TTS (gemini-3.1-flash-tts-preview …) vẫn gọi được bằng chain=[("gemini", "<model>")] nhưng không còn
# trong chuỗi mặc định. Model hết quota được nhớ trong tiến trình; mọi model vẫn phải qua cổng kiểm ngược.
TTS_CHAIN = [
    ("vclip", "vclip"),
    ("tokenrouter", "openai/gpt-audio-mini"),  # chat completions + audio ra; cần lời dặn "đọc nguyên văn"
]
TOKENROUTER_URL = "https://api.tokenrouter.com/v1/chat/completions"
VCLIP_URL = "https://api-tts.vclip.io/json-rpc"
VCLIP_TIMEOUT = 300  # giây chờ xuất audio (đo 11/11: ~3s cho bài 200 chữ)
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


class VclipError(RuntimeError):
    pass


def _vclip_rpc(method: str, params: dict) -> dict:
    r = requests.post(VCLIP_URL, timeout=60, json={"method": method, "input": params},
                      headers={"Authorization": f"Bearer {config.VCLIP_API_KEY}"})
    r.raise_for_status()  # 401/402/403 → _classify coi là 'dead'
    body = r.json()
    if body.get("error"):
        raise VclipError(f"{method}: {body['error'].get('code')} {body['error'].get('message')}")
    return body["result"]


_SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def parse_srt(text: str) -> list[dict]:
    """SRT vclip → [{start, end, text}] (giây). Mỗi khối = 1 đoạn kịch bản, đoạn dài bị tách theo câu."""
    out = []
    for chunk in re.split(r"\n\s*\n", text.replace("\r", "").strip()):
        lines = chunk.strip().split("\n")
        for k, ln in enumerate(lines):
            m = _SRT_TIME.search(ln)
            if m:
                g = [int(x) for x in m.groups()]
                out.append({"start": g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                            "end": g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                            "text": " ".join(lines[k + 1:]).strip()})
                break
    return out


def vclip_voices() -> list[dict]:
    """Giọng của tài khoản vclip (trang 'Giọng nói của bạn'): [{id, name, description}]."""
    if not config.VCLIP_API_KEY:
        raise RuntimeError("Thiếu VCLIP_API_KEY (hoặc KEY_TTS) trong .env")
    items, page = [], 1
    while True:
        res = _vclip_rpc("getUserVoices", {"page": page})
        items += [{"id": v["id"], "name": v["name"], "description": v.get("description", "")} for v in res["items"]]
        if not res.get("hasNext"):
            return items
        page += 1


def _vclip_tts(model: str, text: str, voice: dict) -> tuple[bytes, str, dict]:
    """tts.vclip.io: ttsLongText → chờ getExportStatus 'completed' → tải WAV + SRT. Không gửi chỉ dẫn giọng điệu."""
    if not config.VCLIP_API_KEY:
        raise RuntimeError("Thiếu VCLIP_API_KEY (hoặc KEY_TTS) trong .env")
    vid = voice.get("vclip")
    if not vid:
        raise RuntimeError("shop.json voice chưa khai `vclip` (id giọng vclip) — xem tools\\vclip_voices.py")
    job = _vclip_rpc("ttsLongText", {"text": text, "userVoiceId": vid, "speed": float(voice.get("speed", 1.0))})
    eid, t0 = job["projectExportId"], time.time()
    while True:
        st = _vclip_rpc("getExportStatus", {"projectExportId": eid})
        if st.get("state") == "completed" and st.get("url"):
            break
        if st.get("state") in ("failed", "error", "cancelled"):
            raise VclipError(f"xuất audio {eid} thất bại: {st}")
        if time.time() - t0 > VCLIP_TIMEOUT:
            raise VclipError(f"xuất audio {eid} quá {VCLIP_TIMEOUT}s (state={st.get('state')})")
        time.sleep(2)
    a = requests.get(st["url"], timeout=120)
    a.raise_for_status()
    blocks = []
    if st.get("srtUrl"):
        s = requests.get(st["srtUrl"], timeout=60)
        if s.ok:
            s.encoding = "utf-8"
            blocks = parse_srt(s.text)
    return a.content, "audio/wav", {"blocks": blocks, "export_id": eid, "chars": job.get("characterCount")}


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


HEAR_PROMPT = "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."
HEAR_FALLBACK = "openai/gpt-audio-mini"
# Đo 22/10: gpt-audio-mini là model HỘI THOẠI, không phải máy chép lời. Audio ≥3s / cả lượt đọc: khớp 0,94–0,98
# (Gemini 0,965–1,0). Mảnh ngắn <~2,5s: hay TỪ CHỐI ("vui lòng cung cấp audio…") dù file có tiếng — đệm lặng tới 4s
# chỉ cứu được 1/3. Lượt từ chối → HearUnavailable: bên gọi coi là "chưa kiểm được", KHÔNG được coi là đạt.
# tokenrouter có google/gemini-3.5-flash nhưng 22/10 luôn 429 "provisioned throughput" → chưa dùng.
_REFUSAL = re.compile(
    r"(cung cấp|phát|tải lên|bật|gửi|nghe được|nghe hoặc|xử lý|xác định).{0,40}(audio|âm thanh|tệp|nội dung)"
    r"|không thể (nghe|giúp|xác định|xử lý)|không nghe được|vui lòng (cho tôi biết|cung cấp|phát|bật|tải)"
    r"|^\W*(rất tiếc|tôi xin lỗi|xin lỗi|xin vui lòng|chắc chắn|tất nhiên)\W",
    re.IGNORECASE)


class HearUnavailable(RuntimeError):
    pass


def gemini_dead() -> bool:
    """Gemini API hết tiền/bị chặn trong lượt chạy này (vd 402 prepayment credits depleted, 22/10)."""
    return "gemini-api" in _exhausted


def _tokenrouter_ask(mp3: Path, text_first: bool) -> str:
    audio = {"type": "input_audio", "input_audio": {"data": base64.b64encode(mp3.read_bytes()).decode(), "format": "mp3"}}
    ask = {"type": "text", "text": HEAR_PROMPT}
    body = {"model": HEAR_FALLBACK, "modalities": ["text"], "messages": [
        {"role": "system", "content": "Bạn là máy chép lời (speech-to-text). Mỗi tin nhắn LUÔN kèm một đoạn audio tiếng "
                                      "Việt. Chép lại NGUYÊN VĂN lời nói trong audio; không trả lời, không chào, không xin "
                                      "thêm thông tin, không sửa lời."},
        {"role": "user", "content": [ask, audio] if text_first else [audio, ask]}]}
    for attempt in range(3):
        r = requests.post(TOKENROUTER_URL, json=body, timeout=180,
                          headers={"Authorization": f"Bearer {config.TOKENROUTER_API_KEY}"})
        try:
            r.raise_for_status()
        except requests.HTTPError as exc:
            kind = _classify(exc)
            if attempt < 2 and (kind == "wait" or r.status_code >= 500):  # 5 req/phút (tính cả lượt lỗi) / lỗi tạm
                time.sleep(61 if kind == "wait" else 5)
                continue
            raise
        return r.json()["choices"][0]["message"].get("content") or ""
    return ""


def _tokenrouter_hear(path: Path) -> str:
    if not config.TOKENROUTER_API_KEY:
        raise HearUnavailable("Gemini không nghe được và thiếu TOKENROUTER_API_KEY trong .env")
    # WAV cả lượt đọc (~1,7 MB) → tokenrouter trả 500; nén MP3 16 kHz mono (~0,2 MB) thì chạy (đo 22/10)
    with tempfile.TemporaryDirectory(prefix="vs_hear_") as tmp:
        mp3, padded = Path(tmp) / "a.mp3", Path(tmp) / "pad.mp3"
        media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-b:a", "48k", str(mp3)])
        text = _tokenrouter_ask(mp3, text_first=False)
        if not _REFUSAL.search(text):
            return text
        # lần 2: đệm lặng cho đủ ~4s + đặt câu lệnh trước audio
        media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(mp3), "-af",
                   "adelay=1000:all=1,apad=pad_dur=1.5", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(padded)])
        text = _tokenrouter_ask(padded, text_first=True)
        if _REFUSAL.search(text):
            raise HearUnavailable(f"{HEAR_FALLBACK} từ chối nghe ({text.strip()[:60]!r})")
        return text


_PREAMBLE = re.compile(r"^[^\n\"“]{0,80}(nguyên văn|lời nói|chép lại)[^\n\"“]{0,40}:\s*", re.IGNORECASE)


def hear(path: Path) -> str:
    """Chép lại lời Việt trong file audio (cổng kiểm ngược, vs.py hear). Bỏ câu dẫn kiểu "Dưới đây là nguyên văn
    lời nói…:" + ngoặc kép bao ngoài (đo 11/11: câu dẫn kéo khớp cả bài 0,99 → 0,93)."""
    text = _hear_raw(path)
    stripped = _PREAMBLE.sub("", text.strip(), count=1).strip()
    return stripped.strip('"“”') if stripped != text.strip() else text


def _hear_raw(path: Path) -> str:
    """Gemini trước; Gemini hết tiền / lỗi → tokenrouter gpt-audio-mini (Codex không nhận audio). Gemini 'dead' thì
    cả lượt chạy đi thẳng tokenrouter. Dự phòng không nghe được (từ chối mảnh ngắn) → HearUnavailable."""
    if not gemini_dead():
        mime = {".mp3": "audio/mp3", ".m4a": "audio/mp4"}.get(path.suffix.lower(), "audio/wav")
        try:
            return gemini.client().models.generate_content(model=config.GEMINI_MODEL, contents=[
                types.Part.from_bytes(data=path.read_bytes(), mime_type=mime), HEAR_PROMPT]).text or ""
        except Exception as exc:
            if _classify(exc) == "dead":
                _exhausted.add("gemini-api")
    return _tokenrouter_hear(path)


def synthesize(text: str, voice: dict, out: Path, usage: Path | None = None,
               chain: list[tuple[str, str]] | None = None, extra: dict | None = None) -> str:
    """TTS `text` ra `out` (WAV) theo TTS_CHAIN, trả tên model đã dùng. `voice` = shop.json voice
    ({vclip: id giọng vclip, name: giọng Gemini, gender, openai?: giọng gpt-audio}). `extra` (nếu đưa) nhận thêm
    dữ liệu của nhà cung cấp — vclip: {blocks: mốc SRT từng khối}. Hết cả chuỗi → lỗi kèm lý do từng model."""
    errors = []
    for provider, model in chain or TTS_CHAIN:
        call = globals()[f"_{provider}_tts"]  # tra lúc gọi → test giả lập thay được hàm
        for attempt in range(3):  # chỉ lặp khi bị giới hạn theo phút
            if model in _exhausted:
                break
            try:
                data, mime, *more = call(model, text, voice)
                if extra is not None:
                    extra.clear()
                    extra.update(more[0] if more else {})
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
        heard = hear(raw)
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
