"""So độ "đọc nguyên văn" của các model TTS × kiểu prompt trên câu ngắn dễ bị đọc tiếp."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from google.genai import types  # noqa: E402

from studio import config, gemini  # noqa: E402
from studio.voice import _match, _save_audio, _wav_duration  # noqa: E402

TEXT = "Đánh dấu vị trí bằng bút."
PROMPTS = {
    "plain": TEXT,
    "say": f"Say: {TEXT}",
    "tag": f"Đọc to câu sau rồi dừng lại ngay:\n<text>{TEXT}</text>",
}
out_dir = config.JOBS / "_probe" / "literal"
out_dir.mkdir(parents=True, exist_ok=True)
for model in ("gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"):
    for pname, prompt in PROMPTS.items():
        try:
            r = gemini.client().models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(
                response_modalities=["AUDIO"], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")))))
            p = r.candidates[0].content.parts[0]
            f = out_dir / f"{model}_{pname}.wav"
            _save_audio(p.inline_data.data, p.inline_data.mime_type, f)
            heard = gemini.client().models.generate_content(model=config.GEMINI_MODEL, contents=[
                types.Part.from_bytes(data=f.read_bytes(), mime_type="audio/wav"),
                "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."]).text or ""
            print(f"{model:30} {pname:6} {_wav_duration(f):5.2f}s khớp {_match(TEXT, heard):.2f}  {heard.strip()[:80]!r}")
        except Exception as exc:
            print(f"{model:30} {pname:6} LỖI {type(exc).__name__}: {str(exc)[:100]}")
