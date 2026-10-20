"""Thăm dò: hỏi Gemini 2 đầu dòng chữ (trái/phải) thay vì số góc → tự tính góc, tránh nhập nhằng dấu."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import gemini  # noqa: E402

frame = Path(sys.argv[1])
schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "text": {"type": "string"},
    "left": {"type": "array", "items": {"type": "integer"}},
    "right": {"type": "array", "items": {"type": "integer"}},
}, "required": ["text", "left", "right"]}}}, "required": ["items"]}
data = gemini.generate_json([gemini.image_part(frame),
    "Với mỗi dòng chữ Hán trong ảnh: left = [y, x] điểm GIỮA cạnh trái của dòng chữ (đầu dòng), right = [y, x] "
    "điểm GIỮA cạnh phải (cuối dòng), toạ độ chuẩn hoá 0-1000 (y tính từ trên xuống)."], schema)
from PIL import Image  # noqa: E402
W, H = Image.open(frame).size
for it in data["items"]:
    (ly, lx), (ry, rx) = it["left"], it["right"]
    dx, dy = (rx - lx) * W / 1000, (ry - ly) * H / 1000
    ang = -math.degrees(math.atan2(dy, dx))  # y ảnh hướng xuống → đổi dấu: dương = đi lên
    print(f"{it['text']:20} left={it['left']} right={it['right']} → góc {ang:+.1f}°")
