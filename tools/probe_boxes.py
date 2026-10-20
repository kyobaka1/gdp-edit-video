"""Thăm dò: gửi N khung trong 1 lần gọi, hỏi ô chữ Trung. In ô pixel để so với truth."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, gemini  # noqa: E402

video = Path(sys.argv[1])
times = [float(t) for t in sys.argv[2].split(",")]
work = config.JOBS / "_probe"
work.mkdir(parents=True, exist_ok=True)
frames = []
for t in times:
    p = work / f"f_{t:06.2f}.jpg"
    subprocess.run([config.FFMPEG, "-y", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1",
                    "-q:v", "3", str(p)], check=True)
    frames.append(p)

schema = {
    "type": "object",
    "properties": {"frames": {"type": "array", "items": {"type": "object", "properties": {
        "frame_index": {"type": "integer"},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "integer"}},
        }, "required": ["text", "box_2d"]}},
    }, "required": ["frame_index", "items"]}}},
    "required": ["frames"],
}
prompt = (
    f"Bạn nhận {len(frames)} khung hình đánh số 0..{len(frames) - 1} theo thứ tự. Với MỖI khung, liệt kê mọi "
    "cụm chữ Trung Quốc (Hán tự) nhìn thấy được. Mỗi cụm một mục: text = chữ đọc được, box_2d = "
    "[ymin, xmin, ymax, xmax] chuẩn hoá 0-1000, bao TRỌN cả nền/khung chứa chữ nếu có. Không có chữ Hán → items rỗng."
)
contents = []
for i, f in enumerate(frames):
    contents += [f"Khung {i}:", gemini.image_part(f)]
contents.append(prompt)
t0 = time.time()
data = gemini.generate_json(contents, schema, usage_log=work / "usage.jsonl", label="probe_boxes")
print(f"{time.time() - t0:.1f}s")
W, H = 1080, 1920
for fr in data["frames"]:
    print(f"t={times[fr['frame_index']]}")
    for it in fr["items"]:
        y0, x0, y1, x1 = it["box_2d"]
        print(f"   {it['text']!r:24} px x={x0 * W // 1000} y={y0 * H // 1000} w={(x1 - x0) * W // 1000} h={(y1 - y0) * H // 1000}")
print((work / "usage.jsonl").read_text(encoding="utf-8").splitlines()[-1])
