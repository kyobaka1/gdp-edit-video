r"""Chạy trọn narration.build trên BẢN SAO một job với model Gemini TTS bị coi là hết quota → kiểm lượt đọc
dự phòng (gpt-audio-mini) qua được cổng kiểm ngược, định vị + cắt từng đoạn. Không đụng job gốc.
Chạy: .venv\Scripts\python.exe tools\probe_narration_fallback.py <job_id>"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, narration, voice  # noqa: E402

src = config.JOBS / sys.argv[1]
dst = config.JOBS / "_probe" / f"fallback_{sys.argv[1]}"
shutil.rmtree(dst, ignore_errors=True)
dst.mkdir(parents=True)
for f in ("meta.json", "edl.json"):
    shutil.copy2(src / f, dst / f)
if "--no-gemini" in sys.argv:  # giả lập Gemini 402 hết tiền: TTS, nghe lại, định vị đều phải tự dự phòng
    voice._exhausted.update({"gemini-3.1-flash-tts-preview", "gemini-3.8-flash-tts", "gemini-api"})
rep = narration.build(dst)
print("model:", rep["model"], "| định vị:", rep["align"], "| khớp cả bài:", rep["match"], "| dài:", rep["take_seconds"], "s")
for p in rep["pieces"]:
    print(f"  đoạn {p['index']}: at {p['at']} → {p['start']}–{p['end']}s khớp {p['match']} | {p['heard'][:70]}")
print("cảnh báo:", json.dumps(rep["warnings"], ensure_ascii=False, indent=1))
