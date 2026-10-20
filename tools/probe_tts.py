"""Thăm dò Gemini TTS tiếng Việt: đọc 1 câu, ghi WAV, in thời lượng. Chạy: python tools/probe_tts.py <model> <voice>"""

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from google.genai import types  # noqa: E402

from studio import config, gemini  # noqa: E402

model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash-tts"
voice = sys.argv[2] if len(sys.argv) > 2 else "Kore"
text = "Kệ treo tường không cần khoan. Nhỏ gọn mà chứa nhiều, một kệ gọn mọi đồ nhà tắm."
resp = gemini.client().models.generate_content(
    model=model,
    contents=("Chỉ đọc NGUYÊN VĂN đoạn trong ngoặc kép, không thêm, không bớt, không nói gì khác. "
              f"Giọng nữ, tự nhiên, ấm áp. \"{text}\""),
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
    ),
)
part = resp.candidates[0].content.parts[0]
data, mime = part.inline_data.data, part.inline_data.mime_type
out = config.JOBS / "_probe" / f"tts_{model}_{voice}.wav"
out.parent.mkdir(parents=True, exist_ok=True)
if data[:4] == b"RIFF":  # đã là WAV hoàn chỉnh
    out.write_bytes(data)
else:  # PCM thô 16-bit mono
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)
with wave.open(str(out)) as w:
    dur = w.getnframes() / w.getframerate()
print(f"{mime} · {dur:.2f}s → {out}")

# Kiểm ngược: cho Gemini nghe lại, chép ra chữ để so với câu gốc
back = gemini.client().models.generate_content(
    model=config.GEMINI_MODEL,
    contents=[types.Part.from_bytes(data=out.read_bytes(), mime_type="audio/wav"),
              "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."],
)
print("gốc :", text)
print("nghe:", (back.text or "").strip())
