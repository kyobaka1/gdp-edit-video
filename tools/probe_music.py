"""Thăm dò Lyria: tạo nhạc nền không lời. Chạy: python tools/probe_music.py <model> <giây>"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from google.genai import types  # noqa: E402

from studio import config, gemini  # noqa: E402

model = sys.argv[1] if len(sys.argv) > 1 else "lyria-3.5"
seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 50
prompt = (f"Instrumental background music for a {seconds}-second product video about a modern bathroom shelf. "
          "Upbeat, clean, light electronic pop, 110 BPM, positive and tidy feeling, no vocals, no lyrics, "
          "steady energy suitable under a voiceover, soft ending.")
resp = gemini.client().models.generate_content(
    model=model, contents=prompt, config=types.GenerateContentConfig(response_modalities=["AUDIO"]))
out_dir = config.JOBS / "_probe"
out_dir.mkdir(parents=True, exist_ok=True)
for i, part in enumerate(resp.candidates[0].content.parts):
    if part.inline_data:
        mime = part.inline_data.mime_type
        ext = {"audio/wav": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3"}.get(mime.split(";")[0], "bin")
        out = out_dir / f"music_{model}_{i}.{ext}"
        out.write_bytes(part.inline_data.data)
        print(mime, len(part.inline_data.data), "bytes →", out)
    elif part.text:
        print("text:", part.text[:300])
